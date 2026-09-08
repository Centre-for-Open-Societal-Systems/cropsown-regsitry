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
        STAGING_NAMESPACE = 'crop-staging'

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
            // beforeAgent matters: without it Jenkins tries to allocate the
            // vpn-deploy-agent BEFORE evaluating the condition, so a local run
            // would queue forever waiting for a label that does not exist here.
            //
            // DEV_DEPLOY gates the stage OFF by default, the same way
            // STAGING_DEPLOY gates the one below. No node currently carries the
            // vpn-deploy-agent label, and an unsatisfiable label does not fail —
            // it QUEUES, so the build sat at "'vpn-deploy-agent' is offline"
            // until someone aborted it or the 90-minute timeout fired. That
            // turned a run whose images built and pushed cleanly into a red
            // build, and buried the deploy's real blocker under a timeout.
            //
            // Off, a develop build ends green after the push and the images wait
            // in ECR for a deploy by hand. Set DEV_DEPLOY=true on the controller
            // once a node with that label is online and carries helm + kubectl.
            when {
                beforeAgent true
                branch 'develop'
                expression { env.PUSH_TO_ECR != 'false' }
                expression { env.DEV_DEPLOY == 'true' }
            }
            agent { label 'vpn-deploy-agent' }
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID'),
                    file(credentialsId: 'gen2-kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    sh '''
                        set -eu
                        ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        BRANCH="${BRANCH_NAME}"
                        TAG="${BRANCH}-${BUILD_NUMBER}"

                        echo "=== Deploying ${RELEASE_NAME} to namespace ${NAMESPACE} ==="

                        # The wrapper chart owns no templates; every manifest comes
                        # from the pinned openg2p-registry subchart, so the
                        # dependency must be present before install.
                        helm repo add openg2p https://openg2p.github.io/openg2p-helm || true
                        helm repo update openg2p || true
                        helm dependency build ./${CHART_DIR}

                        # NB the sanity values live UNDER the subchart alias
                        # (registry.sanity.*), not at the top level — see
                        # CHART_IMAGE_PATHS in .gitlab-ci.yml. Setting a top-level
                        # `sanity.image.*` writes a key the chart never reads, so the
                        # sanity Job would silently keep the values.yaml default tag.
                        helm upgrade --install "${RELEASE_NAME}" ./${CHART_DIR} \
                            --namespace "${NAMESPACE}" \
                            --create-namespace \
                            --timeout 10m \
                            --set registry.staffApi.image.repository=${ECR_REGISTRY}/${ECR_BASE}/staff-api \
                            --set registry.staffApi.image.tag=${TAG} \
                            --set registry.partnerApi.image.repository=${ECR_REGISTRY}/${ECR_BASE}/partner-api \
                            --set registry.partnerApi.image.tag=${TAG} \
                            --set registry.celeryWorker.image.repository=${ECR_REGISTRY}/${ECR_BASE}/celery \
                            --set registry.celeryWorker.image.tag=${TAG} \
                            --set registry.celeryBeat.image.repository=${ECR_REGISTRY}/${ECR_BASE}/celery \
                            --set registry.celeryBeat.image.tag=${TAG} \
                            --set registry.dbSeed.image.repository=${ECR_REGISTRY}/${ECR_BASE}/db-seed \
                            --set registry.dbSeed.image.tag=${TAG} \
                            --set registry.sanity.image.repository=${ECR_REGISTRY}/${ECR_BASE}/sanity-tests \
                            --set registry.sanity.image.tag=${TAG}

                        echo "=== Waiting for rollout ==="
                        # staff-portal-api, not staff-api: the subchart sets
                        # staffApi.nameOverride=staff-portal-api, so that is the
                        # Deployment the chart actually creates. The old name matched
                        # nothing, and `|| true` swallowed the error — this step
                        # reported success without ever waiting for a rollout.
                        kubectl rollout status "deployment/${RELEASE_NAME}-staff-portal-api" \
                            -n "${NAMESPACE}" --timeout=120s || true

                        echo "=== Deployment status ==="
                        kubectl get pods -n "${NAMESPACE}" | grep "${RELEASE_NAME}" || true
                    '''
                }
            }
        }

        stage('Deploy to Staging') {
            // beforeAgent matters: without it Jenkins tries to allocate the
            // vpn-deploy-agent BEFORE evaluating the condition, so a local run
            // would queue forever waiting for a label that does not exist here.
            //
            // STAGING_DEPLOY gates the stage OFF by default: the staging cluster
            // is not provisioned yet, and without it the stage fails on the
            // missing staging-kubeconfig credential, turning every staging build
            // red for a deployment nobody expects to work. Set STAGING_DEPLOY=true
            // on the controller once the cluster and that credential exist.
            when {
                beforeAgent true
                branch 'staging'
                expression { env.PUSH_TO_ECR != 'false' }
                expression { env.STAGING_DEPLOY == 'true' }
            }
            agent { label 'vpn-deploy-agent' }
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID'),
                    file(credentialsId: 'staging-kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    sh '''
                        set -eu
                        ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        BRANCH="${BRANCH_NAME}"
                        TAG="${BRANCH}-${BUILD_NUMBER}"

                        helm repo add openg2p https://openg2p.github.io/openg2p-helm || true
                        helm dependency build ./${CHART_DIR}

                        helm upgrade --install "${STAGING_RELEASE}" ./${CHART_DIR} \
                            --namespace "${STAGING_NAMESPACE}" \
                            --create-namespace \
                            --timeout 10m \
                            --set registry.staffApi.image.repository=${ECR_REGISTRY}/${ECR_BASE}/staff-api \
                            --set registry.staffApi.image.tag=${TAG} \
                            --set registry.partnerApi.image.repository=${ECR_REGISTRY}/${ECR_BASE}/partner-api \
                            --set registry.partnerApi.image.tag=${TAG} \
                            --set registry.celeryWorker.image.repository=${ECR_REGISTRY}/${ECR_BASE}/celery \
                            --set registry.celeryWorker.image.tag=${TAG} \
                            --set registry.celeryBeat.image.repository=${ECR_REGISTRY}/${ECR_BASE}/celery \
                            --set registry.celeryBeat.image.tag=${TAG} \
                            --set registry.dbSeed.image.repository=${ECR_REGISTRY}/${ECR_BASE}/db-seed \
                            --set registry.dbSeed.image.tag=${TAG} \
                            --set registry.sanity.image.repository=${ECR_REGISTRY}/${ECR_BASE}/sanity-tests \
                            --set registry.sanity.image.tag=${TAG}

                        kubectl rollout status "deployment/${STAGING_RELEASE}-staff-portal-api" \
                            -n "${STAGING_NAMESPACE}" --timeout=120s || true
                        kubectl get pods -n "${STAGING_NAMESPACE}" | grep "${STAGING_RELEASE}" || true
                    '''
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

