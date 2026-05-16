pipeline {
    agent any

    triggers {
        githubPush()
    }

    environment {
        DOCKERHUB_CREDENTIALS = 'dockerhub-credentials'
        IMAGE_NAME            = 'chanzero11/fastapi-app'
        IMAGE_TAG             = "${env.BUILD_NUMBER}"
        REMOTE_USER           = 'sogang010'
        REMOTE_HOST           = '163.239.77.105'
        REMOTE_PATH           = '/home/sogang010@SGVDI.local/FastApi-Todos'
        REPO_URL              = 'https://github.com/ychanyoung/FastApi-Todos.git'
        BRANCH_NAME           = 'main'
        SONAR_TOKEN           = credentials('sonar-token')
        SONAR_HOST_URL        = 'http://163.239.77.105:9000/'
        JMETER_IMAGE_NAME     = 'my-arm-jmeter'
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
                        def img = docker.build("${IMAGE_NAME}:${IMAGE_TAG}", ".")
                        img.tag("latest")
                    }
                }
            }
        }

        stage('Push') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', DOCKERHUB_CREDENTIALS) {
                        docker.image("${IMAGE_NAME}:${IMAGE_TAG}").push()
                        docker.image("${IMAGE_NAME}:latest").push()
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                sshagent(credentials: ['admin']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} '
                            set -e
                            if [ ! -d ${REMOTE_PATH} ]; then
                                git clone ${REPO_URL} ${REMOTE_PATH}
                            fi
                            cd ${REMOTE_PATH}
                            git fetch origin
                            git reset --hard origin/${BRANCH_NAME}
                            docker compose pull
                            docker compose up -d --build
                            docker compose ps
                        '
                    """
                }
            }
        }

        stage('Build JMeter Image') {
            steps {
                dir('jmeter') {
                    script {
                        docker.build("${JMETER_IMAGE_NAME}:latest", ".")
                    }
                }
            }
        }

        stage('Run JMeter Load Test') {
            steps {
                sh '''
                    BASE_DIR="$WORKSPACE/jmeter"

                    rm -rf "$BASE_DIR/report" "$BASE_DIR/jmeter.log" "$BASE_DIR/results.jtl"
                    mkdir -p "$BASE_DIR/report"

                    TARGET_URL="http://${REMOTE_HOST}:5002"

                    CONTAINER_ID=$(docker create --network host --user root:root ${JMETER_IMAGE_NAME}:latest \
                        sh -c "jmeter -n -t test.jmx -JBASE_URL=$TARGET_URL -l results.jtl -Jjmeter.save.saveservice.output_format=csv -e -o report")

                    docker cp "$BASE_DIR"/*.jmx $CONTAINER_ID:/opt/apache-jmeter-5.4.1/test.jmx

                    docker start -a $CONTAINER_ID || true

                    docker cp $CONTAINER_ID:/opt/apache-jmeter-5.4.1/report "$BASE_DIR/report" || true
                    docker cp $CONTAINER_ID:/opt/apache-jmeter-5.4.1/results.jtl "$BASE_DIR/results.jtl" || true

                    docker rm $CONTAINER_ID
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'jmeter/report/**/*, jmeter/results.jtl', allowEmptyArchive: true
                }
            }
        }

        stage('Health Check') {
            steps {
                sh """
                    sleep 10
                    curl -fsS http://${REMOTE_HOST}:8000/ -o /dev/null && echo 'FastAPI OK'
                    curl -fsS http://${REMOTE_HOST}:9090/-/healthy && echo 'Prometheus OK'
                    curl -fsS http://${REMOTE_HOST}:3000/api/health -o /dev/null && echo 'Grafana OK'
                """
            }
        }
    }

    post {
        always {
            echo 'Pipeline completed.'
        }
        success {
            echo "Deploy success: ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}