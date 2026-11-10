def call() {
// Crop Sown Registry — build, push to ECR, deploy to Kubernetes.
//
//   develop  → build + push → deploy to dev      (release cropsown-registry, namespace crop)
//   staging  → build + push → move staging's app Deployments to the new images
//              (kubectl set image; no helm upgrade, hostnames untouched)
//   other    → build + push only
//
// Shaped after farmer-registry's Jenkinsfile: one linear pipeline, one Deploy
// stage pinned to the `oan-ci-deploy-agent-1` node — the only node that reaches either API
// server — and no build parameters. What the deploy does is chosen by the branch
// below and by ci/deploy-crop-dev.sh's own defaults, so there is nothing to tick
// before a build, and a deploy by hand is the same command:
//
//   KUBECONFIG=<kubeconfig> AWS_ACCOUNT_ID=<id> ./ci/deploy-crop-dev.sh develop-42
//
// Two deliberate differences from farmer-registry's file, both because crop is
// built differently:
//
//   - There is no root Dockerfile with per-component targets here. Each image
//     builds from docker/<name>/Dockerfile with the repo root as context, which
//     is what docker-compose.yml and .gitlab-ci.yml build too.
//   - RP_VERSION is read from docker/staff-api/Dockerfile rather than pinned in
//     this file. The pin already lives in the Dockerfiles, the chart dependency
//     and local/.env, and test/test_rp_pin_lockstep.py guards that those agree —
//     a copy here would be a fourth place to update and the only one no test
//     watches.

pipeline {
    agent any

    environment {
        AWS_REGION     = 'ap-south-1'
        ECR_BASE       = 'openg2p/cropsown-registry'
        // The dashboard service follows the openg2p/<registry>/<image> convention.
        DASHBOARD_API_ECR = 'openg2p/cropsown-registry/dashboard-api'
        DASHBOARD_UI_ECR = 'openg2p/cropsown-registry/dashboard-ui'
        // A maintainer's token for now; the GitHub App replaces this credential when it is configured.
        OAN_HELM_CRED_ID = 'oan-helm-fork-token'

        HELM_NAMESPACE = 'crop'

        // Built from docker/<name>/Dockerfile. dashboard-ui is left out: the
        // chart deploys no dashboard, so its image would be published for nothing.
        SERVICES = 'staff-api staff-ui partner-api celery db-seed sanity-tests registry-connector registry-connector-ui'

        // Connectors remain independently operated; this registry builds only its extension.

        // cropsown-registry-dashboard-api lives in its own (public) repository and
        // is built here beside the registry images, as dashboard-api. Each branch
        // builds the dashboard-api branch of the same name and falls back to
        // develop where there is none. Set DASHBOARD_API_REF on the job (a branch
        // or tag) to pin one instead.
        DASHBOARD_API_REPO = 'https://github.com/Centre-for-Open-Societal-Systems/cropsown-registry-dashboard-api.git'
        DASHBOARD_UI_REPO = 'https://github.com/Centre-for-Open-Societal-Systems/oan_cropsown_dashboard.git'

        // How long helm may wait on the chart's post-upgrade hook Jobs, kept WELL
        // inside the Deploy stage's own 60-minute timeout. At the script's 40m
        // default the two nearly met: a build whose hooks failed spent 40 minutes
        // in helm, began printing why, and was cut off mid-diagnostic by the stage
        // timeout — which ends a build ABORTED, the same word Jenkins prints when
        // a person presses Stop, and skips post{failure}, so nobody was told.
        // 20m leaves the script half an hour to roll out, or to explain itself.
        HELM_TIMEOUT = '20m'

        DEVOPS_EMAILS = 'simretyibeltal@gmail.com, pavanns.ns@gmail.com'
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 150, unit: 'MINUTES')
        // Two deploys at once leave the release locked ("another operation is in
        // progress"); a second build waits for the first instead.
        disableConcurrentBuilds()
        // Build agents are on-demand spot machines: if one is reclaimed mid-build,
        // run the build again instead of failing it.
        retry(count: 2, conditions: [agent(), nonresumable()])
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Validate refactor contracts') {
            steps {
                sh 'docker run --rm --network none --entrypoint python -v "$PWD:/work:ro" -w /work openg2p/openg2p-registry-staff-api:1.2.2-rc.614 ci/refactor/check_port.py . cropsown'
                sh 'docker build --quiet -f ci/refactor/profile-tests.Dockerfile -t oan/cropsown-reference-tests:rc557 .'
                sh 'docker run --rm --memory=768m --network none --entrypoint bash -v "$PWD:/work:ro" -w /work -e REGISTRY_EXTENSION_MODULE=openg2p_registry_cropsown_extension -e PYTHONPATH=/work/cropsown-extension/src oan/cropsown-reference-tests:rc557 ci/validate.sh --native'
                sh 'docker run --rm --network none --entrypoint python -v "$PWD:/work:ro" -w /work oan/cropsown-reference-tests:rc557 -m unittest discover -s test -p test_oan_chart.py -v'
                sh 'docker run --rm --network none --entrypoint python -v "$PWD:/work:ro" -w /work oan/cropsown-reference-tests:rc557 -m unittest discover -s test -p test_deployment_guard.py -v'
                sh 'docker run --rm --network none --entrypoint python -v "$PWD:/work:ro" -w /work oan/cropsown-reference-tests:rc557 -m unittest discover -s test -p test_onboarding_runner_failure.py -v'
                sh 'docker run --rm --network none --entrypoint python -v "$PWD:/work:ro" -w /work -e REGISTRY_EXTENSION_MODULE=openg2p_registry_cropsown_extension -e PYTHONPATH=/work/cropsown-extension/src oan/cropsown-reference-tests:rc557 -m unittest discover -s cropsown-extension/tests -p "test_farmer_reference_*.py" -v'
            }
        }

        stage('Validate native metadata and notification mapping') {
            steps {
                sh 'OAN_REFACTOR_TEST_IMAGE=oan/cropsown-reference-tests:rc557 python3 ci/refactor/rehearse_metadata.py cropsown --pipeline'
                sh 'python3 ci/refactor/compare_new_dev.py cropsown'
                archiveArtifacts artifacts: 'ci-output/refactor/new-dev/seed-rehearsal.json,ci-output/refactor/new-dev/comparison.json,ci-output/refactor/NATIVE_NOTIFICATION_PIPELINE.json', allowEmptyArchive: false
            }
        }

        stage('Checkout dashboard-api') {
            // TEMPORARY: cropsown-registry-dashboard-api has not been merged to its
            // staging branch yet, so staging builds skip it ('Update staging
            // images' never uses the dashboard-api image). Drop this `when` once
            // it is merged.
            when { not { branch 'staging' } }
            steps {
                script {
                    // A PR build (BRANCH_NAME PR-<n>) matches on its source branch.
                    def ref = env.DASHBOARD_API_REF
                    if (!ref) {
                        def wanted = env.CHANGE_BRANCH ?: env.BRANCH_NAME
                        def found = wanted && sh(returnStatus: true,
                            script: "git ls-remote --exit-code --heads ${DASHBOARD_API_REPO} 'refs/heads/${wanted}' > /dev/null") == 0
                        ref = found ? wanted : 'develop'
                    }
                    // .build/ is git-ignored, so the clone never enters a commit.
                    sh "rm -rf .build/dashboard-api && git clone --quiet --depth 1 --branch '${ref}' ${DASHBOARD_API_REPO} .build/dashboard-api"
                    if (!fileExists('.build/dashboard-api/Dockerfile')) {
                        error("dashboard-api ${ref} has no Dockerfile: merge the service into that branch of ${DASHBOARD_API_REPO}, or set DASHBOARD_API_REF")
                    }
                    env.DASHBOARD_API_REF_USED = ref
                    env.DASHBOARD_API_SHA = sh(returnStdout: true, script: 'git -C .build/dashboard-api rev-parse --short=12 HEAD').trim()
                    echo "dashboard-api: ${ref} @ ${env.DASHBOARD_API_SHA}"
                    sh 'bash ci/dashboard/verify-api.sh .build/dashboard-api'
                }
            }
        }

        stage('Checkout dashboard-ui') {
            // TEMPORARY: cropsown-registry-dashboard-ui has not been merged to its
            // staging branch yet, so staging builds skip it ('Update staging
            // images' never uses the dashboard-ui image). Drop this `when` once
            // it is merged.
            when { not { branch 'staging' } }
            steps {
                script {
                    // A PR build (BRANCH_NAME PR-<n>) matches on its source branch.
                    def ref = env.DASHBOARD_UI_REF
                    if (!ref) {
                        def wanted = env.CHANGE_BRANCH ?: env.BRANCH_NAME
                        def found = wanted && sh(returnStatus: true,
                            script: "git ls-remote --exit-code --heads ${DASHBOARD_UI_REPO} 'refs/heads/${wanted}' > /dev/null") == 0
                        ref = found ? wanted : 'develop'
                    }
                    // .build/ is git-ignored, so the clone never enters a commit.
                    sh "rm -rf .build/dashboard-ui && git clone --quiet --depth 1 --branch '${ref}' ${DASHBOARD_UI_REPO} .build/dashboard-ui"
                    if (!fileExists('.build/dashboard-ui/Dockerfile')) {
                        error("dashboard-ui ${ref} has no Dockerfile: merge the service into that branch of ${DASHBOARD_UI_REPO}, or set DASHBOARD_UI_REF")
                    }
                    env.DASHBOARD_UI_REF_USED = ref
                    env.DASHBOARD_UI_SHA = sh(returnStdout: true, script: 'git -C .build/dashboard-ui rev-parse --short=12 HEAD').trim()
                    echo "dashboard-ui: ${ref} @ ${env.DASHBOARD_UI_SHA}"
                    sh 'bash ci/dashboard/verify-source.sh .build/dashboard-ui'
                }
            }
        }

        stage('Guard: openg2p-registry pin lockstep') {
            // Images built FROM one platform version while the chart pulls a
            // subchart expecting another is invisible until the deploy fails.
            // The check is stdlib-only, so it needs no pip on the agent.
            steps {
                sh '''
                    set -eu

                    # The pin check is stdlib-only by design, so a missing pytest is
                    # not a reason to fail the build — run it directly instead.
                    #
                    # This stage used to bootstrap pytest and send the install error
                    # to /dev/null, which turned an agent without python3-pip into a
                    # build failure reading "No module named pytest": the symptom,
                    # never the cause. Ubuntu 22.04 ships python3 with no pip and
                    # ensurepip stripped out, so that agent could not self-heal.
                    if python3 -c 'import pytest' 2>/dev/null; then
                        python3 -m pytest test/test_rp_pin_lockstep.py -q
                    else
                        echo "note: pytest unavailable on this agent — running the guard directly"
                        python3 test/test_rp_pin_lockstep.py
                    fi
                '''
            }
        }

        stage('Resolve version') {
            steps {
                script {
                    env.RP_VERSION = sh(
                        script: "sed -n 's/^ARG RP_VERSION=//p' docker/staff-api/Dockerfile | head -1",
                        returnStdout: true
                    ).trim()
                    if (!env.RP_VERSION) {
                        error 'could not read ARG RP_VERSION from docker/staff-api/Dockerfile'
                    }
                    env.IMAGE_TAG = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
                    echo "openg2p-registry ${env.RP_VERSION}, image tag ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Build & Push') {
            when { allOf { not { changeRequest() }; anyOf { branch 'develop'; branch 'staging' }
                           expression { !((env.NEW_DEV_DELIVERY_ACTION ?: 'deploy') in ['connector-plan', 'connector-upgrade']) } } }
            // Per-build Docker config: login, push and logout never touch the agent user's shared ~/.docker/config.json, so concurrent builds on one host cannot invalidate each other's ECR credentials.
            environment { DOCKER_CONFIG = "${env.WORKSPACE}/.docker-${env.BUILD_TAG}" }
            steps {
                // AWS_ACCOUNT_ID stays inside this block: a bound credential is
                // masked in the log only where it is in scope.
                withCredentials([string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID')]) {
                    sh '''
                        set -eu
                        ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

                        # Keep the buildx/compose CLI plugins visible from the per-build config dir.
                        mkdir -p "$DOCKER_CONFIG"; chmod 700 "$DOCKER_CONFIG"; if [ -d "$HOME/.docker/cli-plugins" ]; then ln -sfn "$HOME/.docker/cli-plugins" "$DOCKER_CONFIG/cli-plugins"; fi

                        aws ecr get-login-password --region "${AWS_REGION}" \
                            | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

                        # The images of this build, for the stage 'Package chart':
                        # values path, repository, tag@digest.
                        : > chart-images.tsv
                        record_image() {
                            DIGEST=$(aws ecr describe-images --region "${AWS_REGION}" --repository-name "$2" \
                                --image-ids imageTag="$3" --query 'imageDetails[0].imageDigest' --output text)
                            printf '%s\\t%s\\t%s@%s\\n' "$1" "${ECR_REGISTRY}/$2" "$3" "$DIGEST" >> chart-images.tsv
                        }

                        for SVC in ${SERVICES}; do
                            IMAGE="${ECR_REGISTRY}/${ECR_BASE}/${SVC}"
                            echo "--- ${SVC} -> ${IMAGE}:${IMAGE_TAG} ---"

                            # --pull, not --no-cache: unchanged layers are reused,
                            # but a moved base tag is still refreshed. Build agents are
                            # on-demand and start with an empty Docker cache, so layers
                            # come from the branch image in ECR (inline cache metadata).
                            docker build --pull \
                                --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from "${IMAGE}:${BRANCH_NAME}" \
                                --build-arg RP_VERSION="${RP_VERSION}" \
                                -f "docker/${SVC}/Dockerfile" \
                                -t "${IMAGE}:${IMAGE_TAG}" -t "${IMAGE}:${BRANCH_NAME}" .

                            # ECR does not create repositories on push.
                            aws ecr describe-repositories --region "${AWS_REGION}" \
                                --repository-names "${ECR_BASE}/${SVC}" >/dev/null 2>&1 \
                              || aws ecr create-repository --region "${AWS_REGION}" \
                                    --repository-name "${ECR_BASE}/${SVC}" >/dev/null

                            docker push "${IMAGE}:${IMAGE_TAG}"
                            docker push "${IMAGE}:${BRANCH_NAME}"
                            case "${SVC}" in
                                staff-api) record_image registry.staffApi.image "${ECR_BASE}/${SVC}" "${IMAGE_TAG}" ;;
                                staff-ui) record_image registry.staffUi.image "${ECR_BASE}/${SVC}" "${IMAGE_TAG}" ;;
                                partner-api) record_image registry.partnerApi.image "${ECR_BASE}/${SVC}" "${IMAGE_TAG}" ;;
                                celery)
                                    record_image registry.celeryWorker.image "${ECR_BASE}/${SVC}" "${IMAGE_TAG}"
                                    record_image registry.celeryBeat.image "${ECR_BASE}/${SVC}" "${IMAGE_TAG}" ;;
                                db-seed) record_image registry.dbSeed.image "${ECR_BASE}/${SVC}" "${IMAGE_TAG}" ;;
                                sanity-tests) record_image registry.sanity.image "${ECR_BASE}/${SVC}" "${IMAGE_TAG}" ;;
                            esac

                            # The connector image carries the OAN extension:
                            # its tests run inside the pushed image.
                            if [ "${SVC}" = registry-connector ]; then
                                docker run --rm -u 0 -v "$PWD/docker/registry-connector:/ext:ro" -w /ext \
                                    -e PYTHONDONTWRITEBYTECODE=1 --entrypoint sh "${IMAGE}:${IMAGE_TAG}" \
                                    -c 'pip install --quiet --no-cache-dir --root-user-action=ignore pytest==8.4.2 && python -m pytest -q -p no:cacheprovider tests'
                            fi

                            # Drop the build tag, keep the branch tag: it is the
                            # next build's cache.
                            docker rmi "${IMAGE}:${IMAGE_TAG}" || true
                        done

                        if [ -n "${DASHBOARD_UI_SHA:-}" ]; then
                            UI_IMAGE="${ECR_REGISTRY}/${DASHBOARD_UI_ECR}:${DASHBOARD_UI_SHA}"
                            docker build --label org.opencontainers.image.revision="${DASHBOARD_UI_SHA}" \
                              -f .build/dashboard-ui/Dockerfile -t "$UI_IMAGE" .build/dashboard-ui
                            docker push "$UI_IMAGE"
                            record_image dashboardUi.image "${DASHBOARD_UI_ECR}" "${DASHBOARD_UI_SHA}"
                        fi
                        # Skipped when 'Checkout dashboard-api' did not run (staging).
                        if [ -n "${DASHBOARD_API_SHA:-}" ]; then
                            # The dashboard service, from its own repository (cloned by
                            # 'Checkout dashboard-api'), with its own build context.
                            IMAGE="${ECR_REGISTRY}/${DASHBOARD_API_ECR}"
                            echo "--- dashboard-api (${DASHBOARD_API_REF_USED} @ ${DASHBOARD_API_SHA}) -> ${IMAGE}:${IMAGE_TAG} ---"
                            docker build --pull \
                                --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from "${IMAGE}:${BRANCH_NAME}" \
                                --label org.opencontainers.image.source="${DASHBOARD_API_REPO}" \
                                --label org.opencontainers.image.revision="${DASHBOARD_API_SHA}" \
                                --label org.opencontainers.image.ref.name="${DASHBOARD_API_REF_USED}" \
                                -f .build/dashboard-api/Dockerfile \
                                -t "${IMAGE}:${IMAGE_TAG}" -t "${IMAGE}:${BRANCH_NAME}" .build/dashboard-api
                            docker push "${IMAGE}:${IMAGE_TAG}"
                            docker push "${IMAGE}:${BRANCH_NAME}"
                            record_image dashboardApi.image "${DASHBOARD_API_ECR}" "${IMAGE_TAG}"
                            docker rmi "${IMAGE}:${IMAGE_TAG}" || true
                        fi

                        # An ECR pull token for the deploy node to write into the
                        # namespace's imagePullSecret. The cluster's own
                        # ecr-refresh CronJob is broken, its 12-hour token expired,
                        # and every pod in the release went ImagePullBackOff —
                        # which helm reported only as the db-seed hook failing with
                        # BackoffLimitExceeded. This agent is the one with AWS
                        # credentials, so the token is minted here and carried over
                        # in the stash below.
                        umask 077
                        aws ecr get-login-password --region "${AWS_REGION}" > .ecr-token
                        echo "${ECR_REGISTRY}" > .ecr-registry
                    '''
                }
                stash name: 'chart-images', includes: 'chart-images.tsv'
            }
        }

        stage('Resolve connector image') {
            // The connector actions build nothing: they take the connector image
            // already in ECR and pin the release to its digest.
            when { allOf { branch 'develop'; expression { (env.NEW_DEV_DELIVERY_ACTION ?: 'deploy') in ['connector-plan', 'connector-upgrade'] } } }
            steps {
                withCredentials([string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID')]) {
                    script {
                        def tag = (env.CONNECTOR_IMAGE_TAG ?: 'develop').trim()
                        if (!(tag ==~ /[A-Za-z0-9._-]{1,128}/)) {
                            error "CONNECTOR_IMAGE_TAG must match [A-Za-z0-9._-]{1,128}; got '${tag}'"
                        }
                        // The service image (api, worker, beat) and the UI image come from the same
                        // build, so one tag resolves to one digest in each repository.
                        env.CONNECTOR_IMAGE_REPOSITORY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BASE}/registry-connector"
                        env.CONNECTOR_UI_IMAGE_REPOSITORY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BASE}/registry-connector-ui"
                        def resolved = [:]
                        ['registry-connector', 'registry-connector-ui'].each { name ->
                            def digest
                            try {
                                digest = sh(returnStdout: true, script: """
                                    aws ecr describe-images --region "${AWS_REGION}" --repository-name "${ECR_BASE}/${name}"                                         --image-ids imageTag="${tag}" --query 'imageDetails[0].imageDigest' --output text
                                """).trim()
                            } catch (err) {
                                error "image ${ECR_BASE}/${name}:${tag} was not found in ECR (${err.message})"
                            }
                            if (!(digest ==~ /sha256:[0-9a-f]{64}/)) {
                                error "could not resolve ${ECR_BASE}/${name}:${tag} to a digest"
                            }
                            echo "connector image ${ECR_BASE}/${name}:${tag} = ${digest}"
                            resolved[name] = digest
                        }
                        env.CONNECTOR_IMAGE_DIGEST = resolved['registry-connector']
                        env.CONNECTOR_UI_IMAGE_DIGEST = resolved['registry-connector-ui']
                    }
                }
            }
        }

        stage('Stash deploy') {
            when { allOf { not { changeRequest() }; anyOf { branch 'develop'; branch 'staging' } } }
            // The deploy node needs the chart, the scripts and the pull token —
            // not the build context, and not a checkout of its own: it deploys
            // exactly this commit without needing GitHub access.
            steps {
                sh 'docker run --rm --user "$(id -u):$(id -g)" --entrypoint python -v "$PWD:/work" -w /work openg2p/openg2p-registry-staff-api:1.2.2-rc.614 ci/deploy/oan_chart.py prefetch registry'
                sh 'docker run --rm --user "$(id -u):$(id -g)" --entrypoint python -v "$PWD:/work" -w /work openg2p/openg2p-registry-staff-api:1.2.2-rc.614 ci/deploy/oan_chart.py prefetch dashboard'
                stash name: 'deploy', includes: "ci/**,.central-charts/**,.ecr-token,.ecr-registry"
                // Stashed; keep the credential out of the build agent's workspace.
                sh 'rm -f .ecr-token .ecr-registry'
            }
        }

        stage('Upgrade connector (New Dev)') {
            // The cropsown-connector release (namespace crop): ci/deploy/connector-chart
            // with the release's current values and the image from 'Resolve connector
            // image'. Upgrade only; the connector database is archived to the New Dev
            // box first.
            when {
                beforeAgent true
                branch 'develop'
                expression { env.NEW_DEV_DELIVERY_ACTION in ['connector-plan', 'connector-upgrade'] }
            }
            agent { label 'oan-ci-deploy' }
            steps {
                sh 'rm -rf ci helm'
                unstash 'deploy'
                script {
                    if (env.NEW_DEV_DELIVERY_ACTION == 'connector-plan') {
                        withCredentials([file(credentialsId: 'crop-dev-kubeconfig', variable: 'KUBECONFIG')]) {
                            sh 'PLAN_ONLY=1 bash ci/deploy/upgrade-crop-connector.sh'
                        }
                    } else {
                        withCredentials([file(credentialsId: 'crop-dev-kubeconfig', variable: 'KUBECONFIG'),
                                         sshUserPrivateKey(credentialsId: 'farmer-new-dev-backup-ssh', keyFileVariable: 'BACKUP_SSH_KEY')]) {
                            sh 'bash ci/deploy/upgrade-crop-connector.sh'
                        }
                    }
                }
            }
        }

        stage('Package chart') {
            // helm/openg2p-cropsown-registry with this build's images. The deploy installs this archive
            // and 'Publish chart' publishes the same one, so what runs on New Dev is what oan-helm lists.
            // It needs the git history for the version, so it is not part of the deploy stash.
            when {
                beforeAgent true
                branch 'develop'
                expression { !((env.NEW_DEV_DELIVERY_ACTION ?: 'deploy') in ['publish-only', 'connector-plan', 'connector-upgrade']) }
            }
            agent { label 'oan-ci-deploy' }
            options { timeout(time: 15, unit: 'MINUTES') }
            steps {
                checkout scm
                unstash 'chart-images'
                sh 'bash ci/deploy/package-chart.sh'
                stash name: 'built-chart', includes: 'built-chart/**'
            }
        }

        stage('Deploy') {
            // develop only. Staging is never helm-upgraded by CI: its automatic
            // helm upgrade replaced staging's live release (chart, hosts, a
            // db-seed against its data) and took the site down. A staging build
            // updates images only, in the next stage.
            //
            // beforeAgent: decide before asking for oan-ci-deploy-agent-1, so a build of any
            // other branch never waits on that node.
            when {
                beforeAgent true
                branch 'develop'
                // A branch-index or polled build has no explicit action: it publishes
                // only; deploy and fresh-install are requested on purpose.
                expression { !((env.NEW_DEV_DELIVERY_ACTION ?: 'deploy') in ['publish-only', 'connector-plan', 'connector-upgrade']) }
            }
            agent { label 'oan-ci-deploy' }
            options {
                // Bounded, because an offline oan-ci-deploy-agent-1 does not fail a build —
                // it QUEUES it, to the 150-minute pipeline timeout. 60 covers the
                // wait for the node, helm's 20 minutes of hooks, the rollout waits
                // and the diagnostics on failure.
                timeout(time: 60, unit: 'MINUTES')
            }
            environment {
                // The dev cluster (RKE2 at 10.0.1.58), as its crop-ci service
                // account.
                KUBECONFIG_CREDENTIAL = 'crop-dev-kubeconfig'
                // The subchart rejects release names over 18 characters, and
                // cropsown-registry is 17.
                HELM_RELEASE          = 'cropsown-registry'
                // No BASE_DOMAIN here: ci/deploy-crop-dev.sh's defaults own the
                // hosts — the portal, staff API and partner API on their public
                // *.development.oanstaging.com names and the shared Gateway; the rest on
                // <namespace>.openg2p.test.
            }
            steps {
                // The workspace outlives builds, and nothing cleans a file this
                // commit deleted out of a stash-only checkout.
                sh 'rm -rf ci helm built-chart'
                unstash 'deploy'
                unstash 'built-chart'
                sh 'bash ci/dashboard/validate-deploy-files.sh cropsown'
                withCredentials([
                    string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID'),
                    file(credentialsId: env.KUBECONFIG_CREDENTIAL, variable: 'KUBECONFIG')
                ]) {
                    // catchInterruptions: if the deploy outlives the stage timeout
                    // above, FAIL the build instead of letting the interrupt
                    // propagate. An uncaught one ends the build ABORTED, which
                    // reads as "a person pressed Stop" and skips post{failure}, so
                    // the hang is never mailed — that is how a run ends with
                    // nothing in Post Actions but `docker image prune`. The cost:
                    // a real Stop pressed DURING a deploy now reads FAILED. A Stop
                    // at any other point still reads ABORTED.
                    catchError(buildResult: 'FAILURE', stageResult: 'FAILURE', catchInterruptions: true) {
                        script {
                            if (env.NEW_DEV_DELIVERY_ACTION == 'fresh-install') {
                                // The database archive goes to the New Dev box over the existing backup key.
                                withCredentials([sshUserPrivateKey(credentialsId: 'farmer-new-dev-backup-ssh', keyFileVariable: 'BACKUP_SSH_KEY')]) {
                                    sh 'BUILT_CHART_DIR="$PWD/built-chart" bash ci/deploy/fresh-install-crop-dev.sh "${IMAGE_TAG}"'
                                }
                            } else {
                                sh 'BUILT_CHART_DIR="$PWD/built-chart" bash ci/deploy-crop-dev.sh "${IMAGE_TAG}"'
                            }
                        }
                        sh 'bash ci/dashboard/deploy-ui.sh cropsown "${HELM_NAMESPACE}" "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${DASHBOARD_UI_ECR}" "${DASHBOARD_UI_SHA}"'
                    }
                }
            }
        }

        stage('Update staging images') {
            // staging only, and never helm upgrade, so staging's release, chart,
            // values and hostnames are untouched:
            //   1. ci/staging-set-images.sh moves each app Deployment to this
            //      build's staging-<n> image (kubectl set image), and undoes them
            //      all if a rollout fails;
            //   2. ci/staging-run-db-seed.sh then runs this build's db-seed as a
            //      plain Job, rendered with staging's own release values, so the
            //      seed data on this branch reaches staging's databases.
            // A db-seed failure fails the build; the new images stay.
            when {
                beforeAgent true
                branch 'staging'
            }
            agent { label 'oan-ci-deploy' }
            options {
                // Five rollouts at up to 7 minutes each, db-seed's 15, and the wait
                // for the node.
                timeout(time: 60, unit: 'MINUTES')
            }
            steps {
                sh 'rm -rf ci helm built-chart'
                unstash 'deploy'
                unstash 'built-chart'
                sh 'bash ci/dashboard/validate-deploy-files.sh cropsown'
                withCredentials([
                    string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID'),
                    file(credentialsId: 'staging-rke2-kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    // As in Deploy: a timeout FAILS the build rather than ending it
                    // ABORTED, so the failure mail goes out.
                    catchError(buildResult: 'FAILURE', stageResult: 'FAILURE', catchInterruptions: true) {
                        sh 'bash ci/staging-set-images.sh "${IMAGE_TAG}" --apply'
                        sh 'bash ci/staging-run-db-seed.sh "${IMAGE_TAG}" --apply'
                    }
                }
            }
        }

        stage('Publish chart') {
            // The last stage, after a successful deploy: add the archive of 'Package chart' to repository/develop/
            // of oan-helm. Its workflow updates the index, changelog and rollback history. The Deploy stage
            // catches its own failure, so the result is checked here. If publishing fails the stage is UNSTABLE
            // and says why; New Dev already runs the build.
            when {
                beforeAgent true
                branch 'develop'
                expression { (env.NEW_DEV_DELIVERY_ACTION ?: 'deploy') == 'deploy' && currentBuild.currentResult == 'SUCCESS' }
            }
            agent { label 'oan-ci-deploy' }
            options { timeout(time: 15, unit: 'MINUTES') }
            steps {
                checkout scm
                sh 'rm -rf built-chart'
                unstash 'built-chart'
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    withCredentials([usernamePassword(credentialsId: "${OAN_HELM_CRED_ID}", usernameVariable: 'GH_USER', passwordVariable: 'GH_TOKEN')]) {
                        sh 'bash ci/deploy/publish-chart.sh'
                    }
                }
            }
        }
    }

    post {
        success {
            script {
                mailQuietly(
                    to: notifyList(),
                    subject: "✅ Build SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                    body: """
Crop Sown Registry build succeeded.

Job:        ${env.JOB_NAME}
Branch:     ${env.BRANCH_NAME}
Build:      #${env.BUILD_NUMBER}
Image tag:  ${env.IMAGE_TAG}
Platform:   openg2p-registry ${env.RP_VERSION}
URL:        ${env.BUILD_URL}

Regards,
Jenkins
"""
                )
            }
        }
        failure {
            script {
                mailQuietly(
                    to: notifyList(),
                    subject: "❌ Build FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                    body: """
Crop Sown Registry build or deploy failed.

Job:        ${env.JOB_NAME}
Branch:     ${env.BRANCH_NAME}
Build:      #${env.BUILD_NUMBER}
Image tag:  ${env.IMAGE_TAG}
URL:        ${env.BUILD_URL}

Console:    ${env.BUILD_URL}console

If the images built and pushed they are in ECR under
openg2p/cropsown-registry/*:${env.IMAGE_TAG}, and the deploy can be re-run by hand
from oan-ci-deploy-agent-1 with ci/deploy-crop-dev.sh.

Regards,
Jenkins
"""
                )
            }
        }
        always {
            sh 'docker image prune -f || true'
            sh 'rm -rf "${WORKSPACE}/.docker-${BUILD_TAG}"'
        }
    }
}
}

// Script-level helpers: Groovy does not allow method definitions inside call().
// The DevOps list, plus the commit author unless it is a noreply address.
def notifyList() {
    def email = sh(script: "git log -1 --pretty=format:'%ae'", returnStdout: true).trim()
    def recipients = env.DEVOPS_EMAILS.split(',').collect { it.trim() }
    if (email && !email.contains('noreply')) {
        recipients = [email] + recipients
    }
    return recipients.unique().join(', ')
}

// A controller without SMTP must not turn a green build red.
def mailQuietly(Map args) {
    try {
        mail(args)
    } catch (err) {
        echo "notification not sent: ${err.message}"
    }
}
return this
