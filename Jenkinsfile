pipeline {
    agent any

    triggers {
        githubPush()
    }

    environment {
        DOCKERHUB_CREDENTIALS = 'dockerhub-credentials'
        IMAGE_NAME           = 'chanzero11/fastapi-app'
        REMOTE_USER          = 'sogang010'
        REMOTE_HOST          = '163.239.77.105'
        REMOTE_PATH          = '/home/sogang010@SGVDI.local'
        REPO_URL             = 'https://github.com/ychanyoung/FastApi-Todos.git'
        BRANCH_NAME          = 'main'
        SONAR_TOKEN          = credentials('sonar-token')
        SONAR_HOST_URL       = 'http://163.239.77.105:9000/'
        CONTAINER_NAME       = 'FastApi-app'
        HOST_PORT            = '8003'
        CONTAINER_PORT       = '5001'
    }

    stages {
        stage('Checkout') {
            steps {
                git url: "${REPO_URL}", branch: "${BRANCH_NAME}"
            }
        }

        stage('Setup Environment & Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r fastapi-app/requirements.txt
                    pip install pytest pytest-html pytest-cov
                '''
            }
        }

        stage('Test & Coverage') {
            steps {
                sh '''
                    . venv/bin/activate
                    mkdir -p pytest_report

                    if [ -d "fastapi-app/tests" ]; then
                        cd fastapi-app && pytest tests \
                          --html=../pytest_report/report.html \
                          --self-contained-html \
                          --cov=. \
                          --cov-report=xml:coverage.xml \
                          --cov-report=html:../htmlcov
                    else
                        echo "tests 디렉토리가 없어 테스트를 건너뜁니다."
                        cat > pytest_report/report.html <<'EOF'
<html>
  <body>
    <h1>Pytest Report</h1>
    <p>tests 디렉토리가 없어 테스트를 실행하지 않았습니다.</p>
  </body>
</html>
EOF
                    fi
                '''
            }
            post {
                always {
                    publishHTML(target: [
                        reportName : 'Pytest HTML Report',
                        reportDir  : 'pytest_report',
                        reportFiles: 'report.html',
                        keepAll    : true,
                        alwaysLinkToLastBuild: true,
                        allowMissing: true
                    ])
                    publishHTML(target: [
                        reportName : 'Coverage Report',
                        reportDir  : 'htmlcov',
                        reportFiles: 'index.html',
                        keepAll    : true,
                        alwaysLinkToLastBuild: true,
                        allowMissing: true
                    ])
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                dir('fastapi-app') {
                    script {
                        def scannerHome = tool 'sonar'
                        withSonarQubeEnv('sonarqube') {
                            sh """
                                export SONAR_TOKEN='${SONAR_TOKEN}'
                                "${scannerHome}/bin/sonar-scanner" \
                                  -Dsonar.projectKey=fastapi_project \
                                  -Dsonar.sources=. \
                                  -Dsonar.host.url="${SONAR_HOST_URL}" \
                                  -Dsonar.token="\$SONAR_TOKEN" \
                                  -Dsonar.python.coverage.reportPaths=coverage.xml
                            """
                        }
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build') {
            steps {
                dir('fastapi-app') {
                    script {
                        docker.build("${IMAGE_NAME}:latest", ".")
                    }
                }
            }
        }

        stage('Push') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', DOCKERHUB_CREDENTIALS) {
                        docker.image("${IMAGE_NAME}:latest").push()
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    sshagent(credentials: ['admin']) {
                        sh "ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} 'docker pull ${IMAGE_NAME}:latest'"
                        sh "ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} 'docker rm -f ${CONTAINER_NAME} || true'"
                        sh "ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} 'docker run -d --name ${CONTAINER_NAME} -p ${HOST_PORT}:${CONTAINER_PORT} ${IMAGE_NAME}:latest'"
                    }
                }
            }
        }
    }

    post {
        always {
            echo 'Pipeline completed.'
        }
    }
}
