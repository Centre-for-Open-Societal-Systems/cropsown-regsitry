// Crop Sown Registry — build, publish to ECR and deploy to Kubernetes.
//
// Laid out like farmer-registry's Jenkinsfile: build and push on the build
// agent, stash the chart, then deploy with plain helm on the `vpn-agent2` node,
// keeping the live release's values and changing only the image tags. The
// differences are cropsown's own: the images and ECR path, the `crop` namespace,
// the openg2p-registry pin guard, and the staging deploy and mails.
//
// The kubeconfig is the DEV_KUBECONFIG build parameter. farmer-registry's
// staging-farmer-kubeconfig reaches its own cluster (10.0.1.212), where
// far:farmer-ci has no rights in crop, so every deploy with it stopped at
// "secrets is forbidden". crop and its commons live on the Gen2 cluster
// (10.15.0.1), which gen2-kubeconfig points at; that is the default. Before helm
// runs, the stage prints the server, identity and `kubectl auth can-i` answers,
// and stops if the account cannot deploy crop (helm needs to LIST secrets).
//
// The Staff Portal UI is built from docker/staff-ui (cropsown branding, six
// register tabs, Dashboard button) and deployed as registry.staffUi, like
// farmer-registry's; before this the crop namespace ran the plain platform
// staff-ui image. Its Dashboard button target is baked in at build time from
// DASHBOARD_URL (set it on the controller; unset, the Dockerfile's local default
// applies). dashboard-ui is built and pushed but not deployed.
//
// To run this pipeline against your own machine, see local/jenkins/README.md: it
// sets PUSH_TO_ECR=false, so the build runs and the push and deploy stages skip.

pipeline {
    agent any

    parameters {
        // Which Jenkins kubeconfig credential Deploy to Dev uses.
        //   crop-dev-kubeconfig        the crop-ci service account of the RKE2
        //                              cluster on 10.0.1.166, which holds crop and
        //                              its commons, addressed by that VPC IP
        //                              (vpn-agent2 reaches it). The default.
        //   gen2-kubeconfig            names 10.15.0.1, which vpn-agent2 cannot
        //                              route to; its CA does not sign 10.0.1.166.
        //   staging-farmer-kubeconfig  farmer-registry's cluster (10.0.1.212),
        //                              which has no crop.
        // The Deploy target block in the log names the server and the rights, so
        // a wrong pick is obvious.
        choice(name: 'DEV_KUBECONFIG', choices: ['crop-dev-kubeconfig', 'gen2-kubeconfig', 'staging-farmer-kubeconfig'],
            description: 'Kubeconfig credential for Deploy to Dev (crop namespace).')
    }

    environment {
        AWS_REGION   = 'ap-south-1'
        ECR_BASE     = 'gen2/cropsown-registry'

        HELM_RELEASE   = 'cropsown-registry'
        HELM_NAMESPACE = 'crop'
        HELM_CHART_DIR = 'helm/openg2p-cropsown-registry'

        // The DEV_KUBECONFIG parameter; the default covers the first build after
        // this file lands, before Jenkins has registered the parameter.
        DEV_KUBECONFIG = "${params.DEV_KUBECONFIG ?: 'crop-dev-kubeconfig'}"

        // With gen2-kubeconfig, reach the Gen2 API server on its VPC address rather
        // than the WireGuard one in the kubeconfig (see the Deploy to Dev stage).
        // Empty for any other credential, which is then used as-is.
        DEV_API_SERVER = "${params.DEV_KUBECONFIG == 'gen2-kubeconfig' ? 'https://10.0.1.166:6443' : ''}"

        // Staging: its own RKE2 instance, deployed from the build agent by
        // ci/deploy-staging.sh. The subchart rejects release names over 18
        // characters, hence cropsown-stg.
        STAGING_RELEASE   = 'cropsown-stg'
        STAGING_NAMESPACE = 'crop'
        NAMESPACE         = 'crop'
        RELEASE_NAME      = 'cropsown-registry'
        CHART_DIR         = 'helm/openg2p-cropsown-registry'

        SERVICES = 'staff-api staff-ui partner-api celery db-seed sanity-tests dashboard-ui'

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

                        # staff-ui bakes the Dashboard button's target in; its patch
                        # fails on an empty URL, so pass it only when set.
                        if [ -n "${DASHBOARD_URL:-}" ]; then
                            PORTAL_ARG="${PORTAL_ARG} --build-arg DASHBOARD_URL=${DASHBOARD_URL}"
                        else
                            echo "WARNING: DASHBOARD_URL unset — staff-ui's Dashboard button points at the local dashboard"
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

        stage('Deploy to Dev (crop namespace)') {
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
                    file(credentialsId: env.DEV_KUBECONFIG, variable: 'KUBECONFIG')
                ]) {
                    sh '''
                        set -eu
                        ECR="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BASE}"
                        VALUES="$(mktemp)"
                        trap 'rm -f "$VALUES"' EXIT

                        # gen2-kubeconfig names the Gen2 API server by its WireGuard
                        # address, 10.15.0.1, which vpn-agent2 cannot route to (every
                        # call timed out). The same RKE2 server listens on its VPC
                        # address, 10.0.1.166, which vpn-agent2 does reach — it deploys
                        # 10.0.1.212 in that VPC. So dial the VPC address on a private
                        # copy of the kubeconfig. The server's certificate lists
                        # 10.0.1.166 among its names (not 10.15.0.1), so it verifies
                        # as-is, with no TLS override.
                        if [ -n "${DEV_API_SERVER:-}" ]; then
                            KCOPY="$(mktemp)"
                            trap 'rm -f "$VALUES" "$KCOPY"' EXIT
                            cp "$KUBECONFIG" "$KCOPY"; export KUBECONFIG="$KCOPY"
                            CLUSTER="$(kubectl config view --minify -o jsonpath='{.contexts[0].context.cluster}')"
                            kubectl config set-cluster "$CLUSTER" --server="${DEV_API_SERVER}" >/dev/null
                        fi

                        # Fail fast on a connection problem, instead of four can-i
                        # calls each retrying for minutes.
                        if ! CONN="$(kubectl get --raw /version --request-timeout=15s 2>&1)"; then
                            echo "ERROR: cannot connect to $(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}') from $(hostname):" >&2
                            echo "$CONN" | tail -3 >&2
                            echo "  A timeout means no route on TCP 6443 (security group / VPN); an x509 error means" >&2
                            echo "  the certificate does not name that address; Unauthorized means a bad credential." >&2
                            exit 1
                        fi

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
                            echo "ERROR: kubeconfig '${DEV_KUBECONFIG}' may not${MISSING} in namespace ${HELM_NAMESPACE} on the server above." >&2
                            echo "  Either pick a credential for the cluster that holds ${HELM_NAMESPACE} (build parameter" >&2
                            echo "  DEV_KUBECONFIG), or have that cluster's admin grant this account ci/k8s/crop-deploy-rbac.yaml." >&2
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
  staffUi:
    image:
      repository: ${ECR}/staff-ui
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

                        # Keep the release's own values (hostnames, Keycloak and IAM
                        # wiring) and change only what this build owns, as
                        # farmer-registry's pipeline does: the chart defaults render
                        # placeholder *.openg2p.org hosts, so upgrading from the CI
                        # file alone would reset the live environment to them. Only
                        # a missing release (first install) may go ahead without.
                        CURRENT="$(mktemp)"; CURRENT_ERR="$(mktemp)"
                        trap 'rm -f "$VALUES" "$CURRENT" "$CURRENT_ERR" "${KCOPY:-}"' EXIT
                        if ! helm get values "${HELM_RELEASE}" -n "${HELM_NAMESPACE}" -o yaml > "$CURRENT" 2> "$CURRENT_ERR"; then
                            grep -q 'release: not found' "$CURRENT_ERR" || { cat "$CURRENT_ERR" >&2; exit 1; }
                            echo "No ${HELM_RELEASE} release in ${HELM_NAMESPACE} yet -- installing with the chart defaults."
                            : > "$CURRENT"
                        fi

                        # When helm fails — most often a post-upgrade hook Job such as
                        # db-seed hitting BackoffLimitExceeded — print why, from the
                        # cluster, into this log. The chart's hooks use
                        # before-hook-creation, so the failed Job and its pods are
                        # still there to read.
                        if ! helm upgrade --install "${HELM_RELEASE}" "${HELM_CHART_DIR}" \
                            -n "${HELM_NAMESPACE}" -f "$CURRENT" -f "$VALUES" --timeout 20m; then
                            echo "=== helm upgrade failed: release history ===" >&2
                            helm history "${HELM_RELEASE}" -n "${HELM_NAMESPACE}" --max 5 >&2 || true
                            for JOB in db-seed sanity; do
                                J="${HELM_RELEASE}-${JOB}"
                                kubectl get job "$J" -n "${HELM_NAMESPACE}" >/dev/null 2>&1 || continue
                                echo "=== Job ${J} ===" >&2
                                kubectl get pods -n "${HELM_NAMESPACE}" -l job-name="$J" -o wide >&2 || true
                                kubectl describe job "$J" -n "${HELM_NAMESPACE}" 2>&1 | tail -25 >&2 || true
                                echo "--- ${J} logs (last pod, all containers) ---" >&2
                                POD="$(kubectl get pods -n "${HELM_NAMESPACE}" -l job-name="$J" \
                                    --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}' 2>/dev/null || true)"
                                [ -z "$POD" ] || kubectl logs "$POD" -n "${HELM_NAMESPACE}" --all-containers --prefix --tail=200 >&2 || true
                            done
                            echo "=== recent warning events ===" >&2
                            kubectl get events -n "${HELM_NAMESPACE}" --field-selector type=Warning \
                                --sort-by=.lastTimestamp 2>/dev/null | tail -20 >&2 || true
                            exit 1
                        fi

                        for D in staff-portal-api staff-portal-ui partner-api celery-worker celery-beat-producer; do
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

A "secrets is forbidden ... in the namespace crop" error means the one-time
kubectl apply -f ci/k8s/crop-deploy-rbac.yaml has not been run by a cluster admin.

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
