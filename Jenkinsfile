// Crop Sown Registry — build, publish to ECR and deploy to Kubernetes.
//
// Laid out like farmer-registry's Jenkinsfile, whose deploy works: build and
// push on the build agent, stash the chart, then deploy with plain helm on the
// `vpn-agent2` node using the `staging-farmer-kubeconfig` credential, into the
// cluster at https://10.0.1.212:6443. The differences are cropsown's own: the
// images and ECR path, the openg2p-registry pin guard, and the staging deploy
// and mails this pipeline already had.
//
// Dev deploys into the `far` namespace, next to farmer-registry. That kubeconfig
// signs in as system:serviceaccount:far:farmer-ci, which may deploy `far` and
// nothing else: every deploy into `crop` failed on "secrets is forbidden", and
// granting it `crop` (ci/k8s/crop-deploy-rbac.yaml) needs a cluster admin on
// 10.0.1.212. The two releases do not collide: the chart names every resource,
// hostname and registry database after the release (cropsown-registry vs
// farmer-registry). The openg2p master-data database is shared between them.
//
// To move to a namespace of its own later: have that cluster's admin apply
// ci/k8s/crop-deploy-rbac.yaml, then set HELM_NAMESPACE back to 'crop'.
//
// The Staff Portal UI is not built: the chart consumes staffUi as-is from the
// platform base image. dashboard-ui is built and pushed but not deployed; the
// chart has no value referencing it yet.
//
// To run this pipeline against your own machine, see local/jenkins/README.md: it
// sets PUSH_TO_ECR=false, so the build runs and the push and deploy stages skip.

pipeline {
    agent any

    environment {
        AWS_REGION   = 'ap-south-1'
        ECR_BASE     = 'gen2/cropsown-registry'

        HELM_RELEASE   = 'cropsown-registry'
        HELM_NAMESPACE = 'far'
        HELM_CHART_DIR = 'helm/openg2p-cropsown-registry'

        // Staging: its own RKE2 instance, deployed from the build agent by
        // ci/deploy-staging.sh. The subchart rejects release names over 18
        // characters, hence cropsown-stg.
        STAGING_RELEASE   = 'cropsown-stg'
        STAGING_NAMESPACE = 'crop'
        NAMESPACE         = 'crop'
        RELEASE_NAME      = 'cropsown-registry'
        CHART_DIR         = 'helm/openg2p-cropsown-registry'

        SERVICES = 'staff-api partner-api celery db-seed sanity-tests dashboard-ui'

        DEVOPS_EMAILS = 'simretyibeltal@gmail.com, pavanns.ns@gmail.com'
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 90, unit: 'MINUTES')
    }

    // develop and staging poll for new commits; every other branch, and the
    // local controller, registers no trigger.
    triggers {
        pollSCM(['develop', 'staging'].contains(env.BRANCH_NAME) && env.PUSH_TO_ECR != 'false' ? 'H/5 * * * *' : '')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Guard: openg2p-registry pin lockstep') {
            // Images built FROM one platform version while the chart pulls a
            // subchart expecting another only shows up at deploy; this catches it
            // in seconds. Plain python3: the agents have no working pip.
            steps {
                sh '''
                    set -eu
                    python3 test/test_rp_pin_lockstep.py
                '''
            }
        }

        stage('Resolve RP_VERSION') {
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
                    echo "openg2p-registry base version: ${env.RP_VERSION}, image tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Build & Push') {
            steps {
                withCredentials([string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID')]) {
                    sh '''
                        set -eu
                        ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        PUSH="${PUSH_TO_ECR:-true}"

                        # Clean builds on the real controller; the local one sets
                        # DOCKER_NO_CACHE=false to iterate faster.
                        CACHE_FLAG="--no-cache"
                        [ "${DOCKER_NO_CACHE:-true}" = "false" ] && CACHE_FLAG=""

                        # dashboard-ui bakes the portal origin into its bundle.
                        PORTAL_ARG=""
                        if [ -n "${PORTAL_URL:-}" ]; then
                            PORTAL_ARG="--build-arg NEXT_PUBLIC_PORTAL_URL=${PORTAL_URL}"
                        else
                            echo "WARNING: PORTAL_URL unset — dashboard-ui bakes in the local portal URL"
                        fi

                        if [ "$PUSH" != "false" ]; then
                            aws ecr get-login-password --region "${AWS_REGION}" \
                                | docker login --username AWS --password-stdin "${ECR_REGISTRY}"
                        fi

                        for SVC in ${SERVICES}; do
                            IMAGE="${ECR_REGISTRY}/${ECR_BASE}/${SVC}"
                            echo "--- ${SVC} -> ${IMAGE}:${IMAGE_TAG} ---"
                            docker build \
                                --build-arg RP_VERSION="${RP_VERSION}" \
                                ${PORTAL_ARG} ${CACHE_FLAG} \
                                -f "docker/${SVC}/Dockerfile" \
                                -t "${IMAGE}:${IMAGE_TAG}" -t "${IMAGE}:${BRANCH_NAME}" .

                            if [ "$PUSH" != "false" ]; then
                                # ECR does not create repositories on push.
                                aws ecr describe-repositories --region "${AWS_REGION}" \
                                    --repository-names "${ECR_BASE}/${SVC}" >/dev/null 2>&1 \
                                  || aws ecr create-repository --region "${AWS_REGION}" \
                                        --repository-name "${ECR_BASE}/${SVC}" >/dev/null
                                docker push "${IMAGE}:${IMAGE_TAG}"
                                docker push "${IMAGE}:${BRANCH_NAME}"
                                docker rmi "${IMAGE}:${IMAGE_TAG}" "${IMAGE}:${BRANCH_NAME}" || true
                            fi
                        done
                    '''
                }
            }
        }

        stage('Stash chart') {
            // Deploy runs on vpn-agent2; carry just the chart over.
            when {
                branch 'develop'
                expression { env.PUSH_TO_ECR != 'false' }
            }
            steps {
                stash name: 'cropsown-chart', includes: "${HELM_CHART_DIR}/**"
            }
        }

        stage('Deploy to Dev (far namespace)') {
            when {
                beforeAgent true
                branch 'develop'
                expression { env.PUSH_TO_ECR != 'false' }
                expression { env.DEV_DEPLOY != 'false' }
            }
            agent { label 'vpn-agent2' }
            steps {
                unstash 'cropsown-chart'
                withCredentials([
                    string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID'),
                    file(credentialsId: 'staging-farmer-kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    sh '''
                        set -eu
                        ECR="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BASE}"
                        VALUES="$(mktemp)"
                        trap 'rm -f "$VALUES"' EXIT

                        # Preflight: name the cluster and account this credential
                        # really uses, and stop before helm if that account cannot
                        # deploy the namespace — so a missing or misplaced
                        # ci/k8s/crop-deploy-rbac.yaml reads as such, with the
                        # server to match against Rancher, not as a helm error.
                        echo "=== Deploy target ==="
                        echo "server:    $(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
                        echo "context:   $(kubectl config current-context 2>/dev/null || echo '(none)')"
                        echo "namespace: ${HELM_NAMESPACE}"
                        kubectl auth whoami 2>/dev/null || true
                        kubectl get ns far "${HELM_NAMESPACE}" 2>&1 || true
                        MISSING=""
                        for CHECK in "list secrets" "create secrets" "create deployments" "create jobs"; do
                            ANSWER="$(kubectl auth can-i ${CHECK} -n "${HELM_NAMESPACE}" 2>&1 || true)"
                            echo "can-i ${CHECK} -n ${HELM_NAMESPACE}: ${ANSWER}"
                            [ "$ANSWER" = "yes" ] || MISSING="${MISSING} '${CHECK}'"
                        done
                        if [ -n "$MISSING" ]; then
                            echo "ERROR: this kubeconfig may not${MISSING} in namespace ${HELM_NAMESPACE} on the server above." >&2
                            echo "  Apply ci/k8s/crop-deploy-rbac.yaml as a cluster admin on THAT cluster (the one whose" >&2
                            echo "  API server is printed above and which has the far namespace), then re-run." >&2
                            exit 1
                        fi

                        helm repo add openg2p https://openg2p.github.io/openg2p-helm || true
                        helm repo update openg2p
                        helm dependency build "${HELM_CHART_DIR}"

                        # Every image path is under the subchart alias (registry.*).
                        cat > "$VALUES" <<EOF
registry:
  staffApi:
    image:
      repository: ${ECR}/staff-api
      tag: "${IMAGE_TAG}"
  partnerApi:
    image:
      repository: ${ECR}/partner-api
      tag: "${IMAGE_TAG}"
  celeryWorker:
    image:
      repository: ${ECR}/celery
      tag: "${IMAGE_TAG}"
  celeryBeat:
    image:
      repository: ${ECR}/celery
      tag: "${IMAGE_TAG}"
  dbSeed:
    image:
      repository: ${ECR}/db-seed
      tag: "${IMAGE_TAG}"
  sanity:
    image:
      repository: ${ECR}/sanity-tests
      tag: "${IMAGE_TAG}"
EOF

                        helm upgrade --install "${HELM_RELEASE}" "${HELM_CHART_DIR}" \
                            -n "${HELM_NAMESPACE}" -f "$VALUES" --timeout 20m

                        for D in staff-portal-api partner-api celery-worker celery-beat-producer; do
                            kubectl rollout status "deployment/${HELM_RELEASE}-${D}" \
                                -n "${HELM_NAMESPACE}" --timeout=180s
                        done

                        echo "=== Jobs ==="
                        kubectl get jobs -n "${HELM_NAMESPACE}" || true
                    '''
                }
            }
        }

        stage('Deploy to Staging') {
            // Unchanged: the staging RKE2 instance, from the build agent, via
            // ci/deploy-staging.sh with staging-rke2-kubeconfig.
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
                    sh './ci/deploy-staging.sh "${BRANCH_NAME}-${BUILD_NUMBER}"'
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
Crop Sown Registry build and deployment succeeded.

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
Crop Sown Registry build or deployment failed.

Job:        ${env.JOB_NAME}
Branch:     ${env.BRANCH_NAME}
Build:      #${env.BUILD_NUMBER}
Console:    ${env.BUILD_URL}console

If Deploy to Dev failed at "Deploy target", the staging-farmer-kubeconfig
account lacks rights in the namespace it names.

Regards,
Jenkins
"""
                )
            }
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}

// The DevOps list always, plus the commit author unless it is a noreply address.
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
