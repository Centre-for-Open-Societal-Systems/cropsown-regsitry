// Crop Sown Registry — build, publish to ECR and deploy to Kubernetes.
//
// This is the SELF-HOSTED pipeline. It is not the same road as .gitlab-ci.yml:
// that one delegates to openg2p/packaging@v1, derives one version per commit and
// publishes to the shared OpenG2P registry + Helm catalogue. This pipeline
// publishes branch-tagged images to a private ECR and rolls them straight into a
// cluster, which is what the dev/staging environments here consume.
//
// Both build exactly the images the Helm chart references, from the same
// docker/*/Dockerfile definitions, so the two never disagree about what the
// registry IS — only about where the artefacts land.
//
// To run this pipeline against your own machine instead of jenkins.oanstaging.com,
// see local/jenkins/README.md: it stands up a controller wired to the local Docker
// daemon with PUSH_TO_ECR=false, so the Build stage runs for real and the ECR/deploy
// stages are skipped until you turn them on.
//
// The Staff Portal UI is deliberately NOT built here:
// helm/openg2p-cropsown-registry/values.yaml consumes staffUi as-is from the
// platform base image, so it has no chart value to point at a build and
// publishing it would produce an image nothing deploys. docker/staff-ui is
// still built by docker-compose.yml for the local stack.
//
// dashboard-ui IS built and published, even though the chart has no value
// referencing it — the analytics dashboard is currently a Compose-only service.
// The image is published so it is ready ahead of the dashboard being deployed;
// until then nothing pulls it.

pipeline {
    agent any

    environment {
        AWS_REGION   = 'ap-south-1'
        ECR_BASE     = 'gen2/cropsown-registry'
        NAMESPACE    = 'crop'
        RELEASE_NAME = 'cropsown-registry'
        CHART_DIR    = 'helm/openg2p-cropsown-registry'

        // Staging carries its own release name rather than "${RELEASE_NAME}-staging".
        // The openg2p-registry subchart rejects any release name over 18 characters
        // (its templates/validate.yaml — longer names push the generated postgres-init
        // Job names past Kubernetes' 63-char label ceiling), and the suffixed form is
        // 25, so that stage could only ever have failed at chart validation.
        STAGING_RELEASE   = 'cropsown-stg'

        // `crop`, the same namespace name dev uses, and not `crop-staging`.
        // Staging is a separate EC2 instance running its own RKE2 cluster,
        // reached through the staging-rke2-kubeconfig credential, so the two
        // environments are held apart by the cluster they land in — this stage
        // shares no API server with the dev deploy above. `crop-staging` only
        // restated a split the kubeconfig already makes, and pointed the deploy
        // at a namespace the staging instance does not use.
        STAGING_NAMESPACE = 'crop'

        // The Jenkins node on the openg2p-Gen2 VPN that deploys dev; see the
        // Deploy to Dev stage.
        DEV_DEPLOY_AGENT = 'vpn-agent2'

        // The five images the chart deploys, matching the IMAGES list in
        // .gitlab-ci.yml. Each builds from docker/<name>/Dockerfile with the repo
        // root as context.
        SERVICES = 'staff-api partner-api celery db-seed sanity-tests dashboard-ui'

        // Always notified, on success and on failure, alongside the commit author.
        DEVOPS_EMAILS = 'simretyibeltal@gmail.com, pavanns.ns@gmail.com'
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 90, unit: 'MINUTES')
    }

    // A merged pull request builds and deploys without anyone pressing Build
    // Now: develop and staging poll the repository and build any new commit.
    // A GitHub webhook to https://jenkins.oanstaging.com/github-webhook/ starts
    // the build at once; polling is what guarantees it when the webhook is
    // missing or a delivery is dropped, and costs one `git ls-remote` per poll.
    //
    // Only the two branches that deploy poll. Every other branch job, and the
    // local controller (PUSH_TO_ECR=false, local/jenkins), gets an empty spec,
    // which registers no trigger — a commit on the laptop does not start six
    // image builds against the local Docker daemon.
    //
    // A trigger is registered when a build reads this file, so the first build
    // of a branch after this lands has to be started once by hand.
    triggers {
        pollSCM(['develop', 'staging'].contains(env.BRANCH_NAME) && env.PUSH_TO_ECR != 'false' ? 'H/5 * * * *' : '')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Guard: openg2p-registry pin lockstep') {
            // The same check .github/workflows/checks.yml runs. It costs seconds
            // and catches the failure that is otherwise invisible until deploy:
            // images built FROM one platform version while the chart pulls a
            // subchart expecting another.
            //
            // Run as a plain script rather than under pytest. The agents carry a
            // python3 but no working pip: the install below used to fail, the
            // `|| true` swallowed it, and the build died one line later on
            // `No module named pytest` — a packaging problem wearing the mask of
            // a failed guard. The check needs nothing beyond the stdlib, so it
            // needs no packaging at all. checks.yml still runs it under pytest.
            steps {
                sh '''
                    set -eu
                    python3 test/test_rp_pin_lockstep.py
                '''
            }
        }

        stage('Resolve RP_VERSION') {
            // Read the pin rather than restating it. A hardcoded copy here would
            // be a fourth place to keep in step with the Dockerfiles, the chart
            // dependency and local/.env — and the one place no test guards.
            steps {
                script {
                    env.RP_VERSION = sh(
                        script: "sed -n 's/^ARG RP_VERSION=//p' docker/staff-api/Dockerfile | head -1",
                        returnStdout: true
                    ).trim()
                    if (!env.RP_VERSION) {
                        error 'could not read ARG RP_VERSION from docker/staff-api/Dockerfile'
                    }
                    echo "openg2p-registry base version: ${env.RP_VERSION}"
                }
            }
        }

        stage('Build Images') {
            steps {
                withCredentials([string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID')]) {
                    sh '''
                        set -eu
                        ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        BRANCH="${BRANCH_NAME}"
                        TAG="${BRANCH}-${BUILD_NUMBER}"

                        # The real controller builds clean so a moved base image
                        # tag is never silently reused. That is minutes per image
                        # per run, which is unaffordable when you are iterating
                        # locally, so the local controller sets DOCKER_NO_CACHE
                        # false. Absent (the real controller), it stays on.
                        CACHE_FLAG="--no-cache"
                        if [ "${DOCKER_NO_CACHE:-true}" = "false" ]; then
                            CACHE_FLAG=""
                            echo "note: building WITH cache (DOCKER_NO_CACHE=false)"
                        fi

                        # dashboard-ui compiles the portal origin into its client
                        # bundle at build time (docker/dashboard-ui/Dockerfile,
                        # ARG NEXT_PUBLIC_PORTAL_URL), so the image is only correct
                        # for the environment named here. Unset, the Dockerfile
                        # default applies — the LOCAL portal — which is wrong for
                        # anything this pipeline publishes.
                        PORTAL_ARG=""
                        if [ -n "${PORTAL_URL:-}" ]; then
                            PORTAL_ARG="--build-arg NEXT_PUBLIC_PORTAL_URL=${PORTAL_URL}"
                        else
                            echo "WARNING: PORTAL_URL unset — dashboard-ui bakes in the local portal URL"
                        fi

                        echo "=== Building images for branch: ${BRANCH} tag: ${TAG} (RP ${RP_VERSION}) ==="

                        for SVC in ${SERVICES}; do
                            echo "--- ${SVC} ---"
                            docker build \
                                --build-arg RP_VERSION="${RP_VERSION}" \
                                --tag "${ECR_REGISTRY}/${ECR_BASE}/${SVC}:${TAG}" \
                                --tag "${ECR_REGISTRY}/${ECR_BASE}/${SVC}:${BRANCH}" \
                                --file "docker/${SVC}/Dockerfile" \
                                ${PORTAL_ARG} ${CACHE_FLAG} .
                        done

                        echo "=== All images built ==="
                    '''
                }
            }
        }

        stage('Push to ECR') {
            // A local run builds and stops there: local/jenkins sets
            // PUSH_TO_ECR=false. Unset — which is every run on the real
            // controller — means push, so this changes nothing there.
            when { expression { env.PUSH_TO_ECR != 'false' } }
            steps {
                withCredentials([string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID')]) {
                    sh '''
                        set -eu
                        ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        BRANCH="${BRANCH_NAME}"
                        TAG="${BRANCH}-${BUILD_NUMBER}"

                        echo "=== Logging in to ECR ==="
                        aws ecr get-login-password --region "${AWS_REGION}" \
                            | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

                        echo "=== Pushing images ==="
                        for SVC in ${SERVICES}; do
                            # Each repository must already exist; ECR does not create
                            # them on push. Created here so a new service does not
                            # fail the first build that adds it.
                            aws ecr describe-repositories \
                                --region "${AWS_REGION}" \
                                --repository-names "${ECR_BASE}/${SVC}" >/dev/null 2>&1 \
                              || aws ecr create-repository \
                                    --region "${AWS_REGION}" \
                                    --repository-name "${ECR_BASE}/${SVC}" >/dev/null

                            docker push "${ECR_REGISTRY}/${ECR_BASE}/${SVC}:${TAG}"
                            docker push "${ECR_REGISTRY}/${ECR_BASE}/${SVC}:${BRANCH}"
                            echo "Pushed ${SVC}:${TAG}"
                        done

                        echo "=== Cleanup local images ==="
                        for SVC in ${SERVICES}; do
                            docker rmi "${ECR_REGISTRY}/${ECR_BASE}/${SVC}:${TAG}" || true
                            docker rmi "${ECR_REGISTRY}/${ECR_BASE}/${SVC}:${BRANCH}" || true
                        done
                        docker system prune -f || true

                        echo "=== All images pushed ==="
                    '''
                }
            }
        }

        stage('Deploy to Dev') {
            // Runs on the `vpn-agent2` node, not on the build agent. The dev
            // cluster's API server (10.15.0.1:6443, behind rancher.openg2p.test)
            // answers only on the openg2p-Gen2 WireGuard VPN. The build agent
            // (an EC2 box) is not on it, so every develop build pushed its images
            // and then timed out on the API server, leaving the crop namespace
            // on the old images. vpn-agent2 is on the VPN.
            //
            // The build agent stashes the chart and the scripts and vpn-agent2
            // deploys from them, so the deploy is exactly this commit. The
            // images are already in ECR, so vpn-agent2 needs no docker or aws
            // CLI; ci/deploy-dev.sh fetches pinned, checksummed helm and kubectl
            // when the node has none. The kubeconfig is `staging-farmer-kubeconfig`,
            // the one farmer-registry's pipeline deploys its `far` namespace with
            // from this same node: crop lives on that cluster too. It signs in as
            // system:serviceaccount:far:farmer-ci, which may deploy crop only
            // after a cluster admin applies ci/k8s/crop-deploy-rbac.yaml once;
            // without it helm fails on "secrets is forbidden ... in the namespace
            // crop". That account cannot create namespaces, so the deploy runs
            // with CREATE_NAMESPACE=false.
            //
            // A node that is offline does not fail a stage, it QUEUES — that is
            // how the old `vpn-deploy-agent` label held builds until the
            // 90-minute timeout. deployOnNode (bottom of this file) bounds the
            // wait: if vpn-agent2 is not free within 30 minutes the build ends
            // UNSTABLE. So does exit 3 from the script (API server unreachable
            // even from vpn-agent2): the images did build and push, the missing
            // piece is the VPN, and the unstable{} post block mails it.
            //
            // The deploy itself is ci/deploy-dev.sh; this stage only supplies
            // the credentials and the tag. It lives in a script so that
            // "deploy by hand" is the same command the pipeline runs, not a
            // helm invocation retyped from this file.
            //
            // DEV_DEPLOY is an opt-OUT, matching STAGING_DEPLOY: set it to
            // 'false' on the controller to hold a develop build at the push and
            // run ci/deploy-dev.sh by hand. Local runs are already excluded by
            // PUSH_TO_ECR=false (local/jenkins), so they need no second flag.
            //
            // beforeAgent is kept so the conditions are evaluated before a node
            // is allocated.
            when {
                beforeAgent true
                branch 'develop'
                expression { env.PUSH_TO_ECR != 'false' }
                expression { env.DEV_DEPLOY != 'false' }
            }
            steps {
                stash name: 'deploy', includes: 'ci/**,helm/**'
                // AWS_REGION, ECR_BASE, NAMESPACE (crop), RELEASE_NAME and
                // CHART_DIR reach the script through the environment block above.
                script { deployOnNode(env.DEV_DEPLOY_AGENT, './ci/deploy-dev.sh', 'dev') }
            }
        }

        stage('Deploy to Staging') {
            // Merging a pull request into `staging` now deploys. The staging
            // instance exists — a separate EC2 box running its own RKE2
            // cluster — so the two reasons this stage was held back are gone:
            //
            //   - It no longer asks for `vpn-deploy-agent`. No node carries that
            //     label, and an unsatisfiable label does not fail a build, it
            //     QUEUES — so the stage sat at "'vpn-deploy-agent' is offline"
            //     until the 90-minute timeout turned a run whose images built
            //     and pushed cleanly into a red build. It runs on the same agent
            //     as the build, which reaches the staging API server through the
            //     kubeconfig below.
            //   - It runs ci/deploy-staging.sh, which is ci/deploy-dev.sh under
            //     the staging release name. This stage used to carry its own copy
            //     of the helm command, and the copy missed the dev deploy's fix
            //     for the agent having no helm or kubectl — the script fetches
            //     pinned copies — so one script now serves both.
            //   - The credential is `staging-rke2-kubeconfig`, the kubeconfig for
            //     that instance's RKE2 cluster, rather than the
            //     `staging-kubeconfig` that was never added to the controller.
            //
            // STAGING_DEPLOY is an opt-OUT, matching the shape of DEV_DEPLOY:
            // set it to 'false' on the controller to hold a staging build at the
            // ECR push and deploy by hand. Local runs are already excluded by
            // PUSH_TO_ECR=false (local/jenkins), so they need no second flag.
            //
            // beforeAgent is kept so the conditions are evaluated before a node
            // is allocated.
            when {
                beforeAgent true
                branch 'staging'
                expression { env.PUSH_TO_ECR != 'false' }
                expression { env.STAGING_DEPLOY != 'false' }
            }
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID'),
                    file(credentialsId: 'staging-rke2-kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    // STAGING_RELEASE and STAGING_NAMESPACE, plus the shared
                    // AWS_REGION, ECR_BASE and CHART_DIR, reach the script
                    // through the environment block above.
                    script { runDeploy('./ci/deploy-staging.sh', 'staging') }
                }
            }
        }
    }

    post {
        success {
            script {
                def to = notifyList()
                mailQuietly(
                    to: to,
                    subject: "✅ Build SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                    body: """
Crop Sown Registry build and deployment succeeded.

Job:        ${env.JOB_NAME}
Branch:     ${env.BRANCH_NAME}
Build:      #${env.BUILD_NUMBER}
Image tag:  ${env.BRANCH_NAME}-${env.BUILD_NUMBER}
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
                def to = notifyList()
                mailQuietly(
                    to: to,
                    subject: "❌ Build FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                    body: """
Crop Sown Registry build or deployment failed.

Job:        ${env.JOB_NAME}
Branch:     ${env.BRANCH_NAME}
Build:      #${env.BUILD_NUMBER}
URL:        ${env.BUILD_URL}

Console:    ${env.BUILD_URL}console

Regards,
Jenkins
"""
                )
            }
        }
        // UNSTABLE is what runDeploy and deployOnNode leave when the cluster, or
        // the dev deploy node, could not be reached: neither success{} nor
        // failure{} fires for it, and a deploy that silently did not happen is
        // the one outcome that must be mailed.
        unstable {
            script {
                def to = notifyList()
                mailQuietly(
                    to: to,
                    subject: "⚠️ Build UNSTABLE: ${env.JOB_NAME} #${env.BUILD_NUMBER} — built, not deployed",
                    body: """
Crop Sown Registry images built and were pushed to ECR, but the deploy could not
reach the cluster, so nothing was deployed.

Job:        ${env.JOB_NAME}
Branch:     ${env.BRANCH_NAME}
Build:      #${env.BUILD_NUMBER}
Image tag:  ${env.BRANCH_NAME}-${env.BUILD_NUMBER}
URL:        ${env.BUILD_URL}

Console:    ${env.BUILD_URL}console

Dev deploys from the vpn-agent2 node, which must be online and on the
openg2p-Gen2 VPN; staging from the build agent with staging-rke2-kubeconfig.
Check the console, fix the route, then re-run the build.

Regards,
Jenkins
"""
                )
            }
        }
    }
}

// Run a deploy script against this build's image tag.
//
// Exit 3 is the scripts' "could not reach the API server": nothing was
// touched, the images are already in ECR, and the fix is a network route, not
// code. That marks the stage FAILED but leaves the build UNSTABLE, so a push
// that succeeded does not read as a broken build. Every other non-zero exit — a
// refused login, a helm error — still fails it.
def runDeploy(String deployScript, String cluster) {
    // Single-quoted tail: the shell, not Groovy, expands the tag.
    def rc = sh(returnStatus: true, script: deployScript + ' "${BRANCH_NAME}-${BUILD_NUMBER}"')
    if (rc == 3) {
        catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
            error "${cluster} cluster unreachable from ${env.NODE_NAME} — nothing deployed; images are in ECR"
        }
    } else if (rc != 0) {
        error "${deployScript} failed (exit ${rc})"
    }
}

// Run a deploy on the named node (one on the cluster's VPN), from the 'deploy'
// stash, with the dev kubeconfig.
//
// The wait for that node is bounded: an offline or busy node leaves the build
// queued, not failed, and the 30 minutes also cover the deploy itself (helm
// waits up to 10 for the chart's hook Jobs). A timeout before the node was
// reached ends the build UNSTABLE, like an unreachable API server; one during
// the deploy is a real hang and aborts it.
def deployOnNode(String label, String deployScript, String cluster) {
    def started = false
    try {
        timeout(time: 30, unit: 'MINUTES') {
            node(label) {
                started = true
                // The workspace outlives builds; clear what an earlier one left so
                // a file this commit deleted cannot linger. .tools/ is kept, so
                // helm and kubectl are fetched once, not per build.
                sh 'rm -rf ci helm'
                unstash 'deploy'
                withCredentials([
                    string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID'),
                    file(credentialsId: 'staging-farmer-kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    // farmer-ci may not manage namespaces; crop is created by
                    // ci/k8s/crop-deploy-rbac.yaml.
                    withEnv(['CREATE_NAMESPACE=false']) {
                        runDeploy(deployScript, cluster)
                    }
                }
            }
        }
    } catch (org.jenkinsci.plugins.workflow.steps.FlowInterruptedException e) {
        if (started) {
            throw e
        }
        catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
            error "'${label}' node not available within 30 minutes — nothing deployed; images are in ECR"
        }
    }
}

// The DevOps list always, plus the commit author when the commit carries a
// usable address. A `noreply` address bounces, so a bot commit notifies the
// list alone rather than mailing into a void.
def notifyList() {
    def email = sh(script: "git log -1 --pretty=format:'%ae'", returnStdout: true).trim()
    def recipients = env.DEVOPS_EMAILS.split(',').collect { it.trim() }
    if (email && !email.contains('noreply')) {
        recipients = [email] + recipients
    }
    return recipients.unique().join(', ')
}

// Local controllers (local/jenkins) have no SMTP, and an unconfigured `mail`
// step throws — which in post{} turns an otherwise green build red. A
// notification that could not be sent has never been a build failure, so it is
// logged and swallowed.
def mailQuietly(Map args) {
    try {
        mail(args)
    } catch (err) {
        echo "notification not sent: ${err.message}"
    }
}

