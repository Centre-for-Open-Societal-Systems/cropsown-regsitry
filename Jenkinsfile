// Crop Sown Registry — build, push to ECR, deploy to Kubernetes.
//
//   develop  → build + push → Deploy to Dev     (namespace crop, RKE2 at 10.0.1.166)
//   staging  → build + push → Deploy to Staging (staging RKE2 instance)
//   other    → build only
//
// Deploy to Dev runs on the `vpn-agent2` node, which reaches the dev API server,
// with the `gen2-dev-kubeconfig` credential (the crop-ci service account, admin
// in `crop`). The deploy itself is ci/deploy-crop-dev.sh, so a manual deploy is
// the same command; see that script for what it does and why.
//
// Build parameters:
//   RUN_DB_SEED  (off)  also run the db-seed hook Job; a deploy is images-only
//   RUN_SANITY   (off)  run the sanity seed + e2e hook Jobs
//   RUN_IAM_REGISTER (off) re-register the app in IAM (needs Keycloak reachable in-cluster)
//   SEED_MINIO_ASSETS (off) db-seed also uploads images/templates (needs MinIO reachable in-cluster)
//
// Controller environment (optional):
//   DEV_DEPLOY=false          build and push develop without deploying
//   STAGING_DEPLOY=false      same for staging
//   PUSH_TO_ECR=false         build only (local/jenkins sets this)
//   DOCKER_NO_CACHE=true      rebuild every image layer
//   BUILD_DASHBOARD_UI=true   also build dashboard-ui (not deployed by the chart)
//   DASHBOARD_URL             staff-ui's Dashboard button target (baked in at build)
//   PORTAL_URL                dashboard-ui's portal origin (baked in at build)

pipeline {
    agent any

    parameters {
        // db-seed is a post-upgrade hook, so when it fails the whole release
        // fails and the images do not go live, even though they pulled and rolled
        // out fine. It is off by default for that reason: a deploy publishes
        // images, and seeding is a deliberate, watched run. Tick it after
        // changing seed SQL or metadata.
        booleanParam(name: 'RUN_DB_SEED', defaultValue: false,
            description: 'Deploy: also run the db-seed Job (seed SQL, metadata, Ethiopia geo). Off = images only.')
        booleanParam(name: 'RUN_SANITY', defaultValue: false,
            description: 'Deploy to Dev: run the sanity seed and e2e test Jobs.')
        // iam-register fetches a token from the PUBLIC Keycloak URL
        // (https://keycloak.crop.openg2p.test), which pods cannot reach, so it
        // retries 30 times and holds the deploy. The app is already registered.
        booleanParam(name: 'RUN_IAM_REGISTER', defaultValue: false,
            description: 'Deploy to Dev: re-run the IAM registration Job.')
        // db-seed's image/template loaders upload to the public MinIO host, which
        // pods cannot reach; off, db-seed loads SQL metadata and geo data only.
        booleanParam(name: 'SEED_MINIO_ASSETS', defaultValue: false,
            description: 'Deploy to Dev: let db-seed upload images and templates to MinIO.')
    }

    environment {
        AWS_REGION     = 'ap-south-1'
        ECR_BASE       = 'gen2/cropsown-registry'

        // Dev deploy (ci/deploy-crop-dev.sh)
        HELM_RELEASE   = 'cropsown-registry'
        HELM_NAMESPACE = 'crop'
        HELM_CHART_DIR = 'helm/openg2p-cropsown-registry'

        // Staging deploy (ci/deploy-staging.sh). The subchart rejects release
        // names over 18 characters, hence cropsown-stg.
        STAGING_RELEASE   = 'cropsown-stg'
        STAGING_NAMESPACE = 'crop'
        NAMESPACE         = 'crop'
        RELEASE_NAME      = 'cropsown-registry'
        CHART_DIR         = 'helm/openg2p-cropsown-registry'

        // Images built from docker/<name>/Dockerfile (repo root as context).
        SERVICES = 'staff-api staff-ui partner-api celery db-seed sanity-tests'

        DEVOPS_EMAILS = 'simretyibeltal@gmail.com, pavanns.ns@gmail.com'
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        // Image builds plus a deploy that waits on the chart's hook Jobs.
        timeout(time: 150, unit: 'MINUTES')
        // Two deploys at once leave the helm release locked ("another operation
        // is in progress"); a second build waits for the first instead.
        disableConcurrentBuilds()
    }

    // develop and staging poll for new commits; other branches and the local
    // controller register no trigger.
    triggers {
        pollSCM(['develop', 'staging'].contains(env.BRANCH_NAME) && env.PUSH_TO_ECR != 'false' ? 'H/5 * * * *' : '')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Guard: openg2p-registry pin lockstep') {
            // Images FROM one platform version with a chart expecting another only
            // fails at deploy; catch it here. Plain python3, no pip needed.
            steps {
                sh 'python3 test/test_rp_pin_lockstep.py'
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
            steps {
                withCredentials([string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID')]) {
                    sh '''
                        set -eu
                        ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        PUSH="${PUSH_TO_ECR:-true}"

                        # Reuse unchanged layers; --pull still refreshes moved base tags.
                        CACHE_FLAG="--pull"
                        if [ "${DOCKER_NO_CACHE:-false}" = "true" ]; then CACHE_FLAG="--pull --no-cache"; fi

                        BUILD_ARGS="--build-arg RP_VERSION=${RP_VERSION}"
                        # Both are baked into client bundles at build time; the staff-ui
                        # patch rejects an empty DASHBOARD_URL, so pass them only when set.
                        if [ -n "${DASHBOARD_URL:-}" ]; then BUILD_ARGS="${BUILD_ARGS} --build-arg DASHBOARD_URL=${DASHBOARD_URL}"; fi
                        if [ -n "${PORTAL_URL:-}" ]; then BUILD_ARGS="${BUILD_ARGS} --build-arg NEXT_PUBLIC_PORTAL_URL=${PORTAL_URL}"; fi

                        BUILD_LIST="${SERVICES}"
                        if [ "${BUILD_DASHBOARD_UI:-false}" = "true" ]; then BUILD_LIST="${BUILD_LIST} dashboard-ui"; fi

                        if [ "$PUSH" != "false" ]; then
                            aws ecr get-login-password --region "${AWS_REGION}" \
                                | docker login --username AWS --password-stdin "${ECR_REGISTRY}"
                        fi

                        for SVC in ${BUILD_LIST}; do
                            IMAGE="${ECR_REGISTRY}/${ECR_BASE}/${SVC}"
                            echo "--- ${SVC} -> ${IMAGE}:${IMAGE_TAG} ---"
                            docker build ${BUILD_ARGS} ${CACHE_FLAG} \
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
                                # Keep the branch tag locally: it is the next build's cache.
                                docker rmi "${IMAGE}:${IMAGE_TAG}" || true
                            fi
                        done

                        # An ECR pull token for the deploy node to put in the
                        # namespace's imagePullSecret. The cluster's own
                        # ecr-refresh CronJob was broken (its ecr-refresh-aws
                        # secret is missing), the 12-hour token expired, and every
                        # pod in the release went ImagePullBackOff — db-seed
                        # included, which is what helm reported as
                        # BackoffLimitExceeded. Only this agent has AWS
                        # credentials, so the token is minted here.
                        if [ "$PUSH" != "false" ]; then
                            umask 077
                            aws ecr get-login-password --region "${AWS_REGION}" > .ecr-token
                            echo "${ECR_REGISTRY}" > .ecr-registry
                        fi
                    '''
                }
            }
        }

        stage('Deploy') {
            // Like farmer-registry's single deploy stage: develop goes to dev and
            // staging to staging, both from the vpn-agent2 node, which is the only
            // node that reaches either API server. The kubeconfig, release,
            // namespace and base domain are chosen by branch below; everything else
            // is ci/deploy-crop-dev.sh, so a deploy by hand is the same command.
            //
            //   develop  gen2-dev-kubeconfig       dev, 10.0.1.166, release
            //                                      cropsown-registry in crop
            //   staging  staging-rke2-kubeconfig   staging, release cropsown-stg
            //                                      in crop (its own cluster)
            when {
                beforeAgent true
                anyOf {
                    branch 'develop'
                    branch 'staging'
                }
                expression { env.PUSH_TO_ECR != 'false' }
                expression { env.BRANCH_NAME == 'develop' ? env.DEV_DEPLOY != 'false' : env.STAGING_DEPLOY != 'false' }
            }
            environment {
                DEPLOY_KUBECONFIG = "${env.BRANCH_NAME == 'staging' ? 'staging-rke2-kubeconfig' : 'gen2-dev-kubeconfig'}"
                DEPLOY_RELEASE    = "${env.BRANCH_NAME == 'staging' ? 'cropsown-stg' : 'cropsown-registry'}"
                // Staging's hosts are whatever that release already carries: the
                // .openg2p.test base domain is the dev environment's. Empty leaves
                // every host value untouched.
                DEPLOY_BASE_DOMAIN = "${env.BRANCH_NAME == 'staging' ? '' : '{{ .Release.Namespace }}.openg2p.test'}"
            }
            steps {
                // The deploy node needs only the chart and the deploy script.
                stash name: 'deploy', includes: "ci/**,${HELM_CHART_DIR}/**,.ecr-token,.ecr-registry"
                // The token is short-lived, but it is a credential: keep it out of
                // the build agent's workspace once it is stashed.
                sh 'rm -f .ecr-token .ecr-registry'
                // Bounded: an offline vpn-agent2 would otherwise queue the build
                // until the pipeline timeout. 60 minutes covers the wait for the
                // node and the deploy (helm waits up to 40 for hooks).
                timeout(time: 60, unit: 'MINUTES') {
                    node('vpn-agent2') {
                        sh 'rm -rf ci helm'
                        unstash 'deploy'
                        withCredentials([
                            string(credentialsId: 'AWS_ACCOUNT_ID', variable: 'AWS_ACCOUNT_ID'),
                            file(credentialsId: env.DEPLOY_KUBECONFIG, variable: 'KUBECONFIG')
                        ]) {
                            // Defaults cover the first build after this file lands,
                            // before Jenkins has registered the parameters.
                            withEnv([
                                "HELM_RELEASE=${env.DEPLOY_RELEASE}",
                                "BASE_DOMAIN=${env.DEPLOY_BASE_DOMAIN}",
                                "RUN_DB_SEED=${params.RUN_DB_SEED == null ? false : params.RUN_DB_SEED}",
                                "RUN_SANITY=${params.RUN_SANITY == null ? false : params.RUN_SANITY}",
                                "RUN_IAM_REGISTER=${params.RUN_IAM_REGISTER == null ? false : params.RUN_IAM_REGISTER}",
                                "SEED_MINIO_ASSETS=${params.SEED_MINIO_ASSETS == null ? false : params.SEED_MINIO_ASSETS}"
                            ]) {
                                sh 'bash ci/deploy-crop-dev.sh "${IMAGE_TAG}"'
                            }
                        }
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
Crop Sown Registry build or deployment failed.

Job:        ${env.JOB_NAME}
Branch:     ${env.BRANCH_NAME}
Build:      #${env.BUILD_NUMBER}
Console:    ${env.BUILD_URL}console

A failed dev deploy prints its reason in the console: the "Deploy target" checks,
then hook pod logs, API pod logs, release history and warning events.

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
