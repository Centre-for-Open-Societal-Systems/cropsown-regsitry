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
// The Staff Portal UI and the analytics dashboard are deliberately NOT built
// here. helm/openg2p-cropsown-registry/values.yaml consumes staffUi as-is from
// the platform base image, and dashboard-ui is a Compose-only service, so
// neither has a chart value to point at a build. Publishing them would produce
// images nothing deploys. (docker/staff-ui and docker/dashboard-ui are still
// built by docker-compose.yml for the local stack.)

pipeline {
    agent any

    environment {
        AWS_REGION   = 'ap-south-1'
        ECR_BASE     = 'gen2/cropsown-registry'
        NAMESPACE    = 'crop'
        RELEASE_NAME = 'cropsown-registry'
        CHART_DIR    = 'helm/openg2p-cropsown-registry'

        // The five images the chart deploys, matching the IMAGES list in
        // .gitlab-ci.yml. Each builds from docker/<name>/Dockerfile with the repo
        // root as context.
        SERVICES = 'staff-api partner-api celery db-seed sanity-tests'

        // Where failure mail goes when the commit has no usable author address.
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
            steps {
                sh '''
                    set -eu
                    python3 -m pip install --quiet --user pytest 2>/dev/null || true
                    python3 -m pytest test/test_rp_pin_lockstep.py -q
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

                        echo "=== Building images for branch: ${BRANCH} tag: ${TAG} (RP ${RP_VERSION}) ==="

                        for SVC in ${SERVICES}; do
                            echo "--- ${SVC} ---"
                            docker build \
                                --build-arg RP_VERSION="${RP_VERSION}" \
                                --tag "${ECR_REGISTRY}/${ECR_BASE}/${SVC}:${TAG}" \
                                --tag "${ECR_REGISTRY}/${ECR_BASE}/${SVC}:${BRANCH}" \
                                --file "docker/${SVC}/Dockerfile" \
                                --no-cache .
                        done

                        echo "=== All images built ==="
                    '''
                }
            }
        }

        stage('Push to ECR') {
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
            when { branch 'develop' }
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
                            --namespace "crop" \
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
                        kubectl rollout status "deployment/${RELEASE_NAME}-staff-api" \
                            -n "${NAMESPACE}" --timeout=120s || true

                        echo "=== Deployment status ==="
                        kubectl get pods -n "${NAMESPACE}" | grep "${RELEASE_NAME}" || true
                    '''
                }
            }
        }

        stage('Deploy to Staging') {
            when { branch 'staging' }
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

                        helm upgrade --install "${RELEASE_NAME}-staging" ./${CHART_DIR} \
                            --namespace "crop-staging" \
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

                        kubectl rollout status "deployment/${RELEASE_NAME}-staging-staff-api" \
                            -n "${NAMESPACE}-staging" --timeout=120s || true
                        kubectl get pods -n "${NAMESPACE}-staging" | grep "${RELEASE_NAME}-staging" || true
                    '''
                }
            }
        }
    }

    post {
        success {
            script {
                def to = committerMail()
                mail(
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
                def to = committerMail()
                mail(
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

// The commit author, or the DevOps list when the commit was made by a bot (a
// `noreply` address bounces, so the notification would be lost).
def committerMail() {
    def email = sh(script: "git log -1 --pretty=format:'%ae'", returnStdout: true).trim()
    return email.contains('noreply') ? env.DEVOPS_EMAILS : email
}
