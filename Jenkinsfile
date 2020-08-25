def nonprodAcct = '345248387622'
def nonprodBucket = 'sts-np-compliance-bundles'
// def prodAcct = '737855703655'
def prodAcct = ''
def prodBucket = 'sts-compliance-bundles'
def functionName = 'Devolumizer'
def repoName = 'aws-Devolumizer'
def region = 'us-east-1'


pipeline {
    agent any 

    environment {
        PATH = "${tool 'terraform-v0.12.10'}:$PATH"
    }

    stages {
        stage(‘Checkout’) { 
        	when { 
            	not { 
                	anyOf { 
                		branch 'PR-*'
            	    } 
                }
            }
            steps {
                
    			checkout scm 

    			}		
            
        }

        
        stage(‘Build’) {
             
            steps {
                sh"""
                cd function
                pip-3.6 install -r requirements.txt -t .
                zip -r9 ../${commitID()}.zip * -x '*.git*' requirements.txt README.md
                """
            }
        }
		
		stage(‘GitHub_Version’) {
        	when { 
                not { 
                    branch 'master' 
                }
            } 
            steps {
               withCredentials([string(credentialsId: 'ba-github-token', variable: 'ba-github-token')]) {
				sh '''
				echo "Publishing on Github..."
				# Create a release
				release=$(curl -XPOST -H "Authorization:token $token" --data "{\"tag_name\": \"$tag\", \"target_commitish\": \"master\", \"name\": \"$name\", \"body\": \"$description\", \"draft\": false, \"prerelease\": true}" https://api.github.com/repos/keepitsts/jenkins-python-aws/releases)
				# Extract the id of the release from the creation response
				id=$(git  rev-parse --short HEAD)
				'''
				}
            }
        }
		
		stage(‘Push_NonProd’) { 
			when { 
                not { 
                    branch 'master' 
                }
            }
            steps {
                withAWS(role: 'JenkinsAssumedRole', roleAccount: nonprodAcct) {
                    sh "aws s3 cp ${commitID()}.zip s3://${nonprodBucket}/${functionName}/${commitID()}.zip"
                }
            }
        }
        
        stage(‘Push_Prod’) { 
			when { 
                branch 'master' 
            }
            steps {

                withAWS(role: 'JenkinsAssumedRole', roleAccount: prodAcct) {
                    sh "aws s3 cp ${commitID()}.zip s3://${prodBucket}/${functionName}/${commitID()}.zip"
                }

            }
        }
        		
        stage(‘Build_Nonprod_Infra’) { 
			when { 
                not { 
                    branch 'master' 
                }
            }
            steps {
               sh"""
                cd nonprod
                echo 'Initializing Terraform...'
                terraform init -input=false
                echo 'Building Infra/Accounting for Drift...'
                terraform apply\
                -var bucket_name=${nonprodBucket}\
                -var function_name=${functionName}\
                -var commit_id=${commitID()}\
                -auto-approve
               """ 
            }
        }

        stage(‘Build_Prod_Infra’) { 
			when { 
                branch 'master' 
            }
            steps {
                sh"""
                cd prod
                echo 'Initializing Terraform...'
                terraform init -input=false
                echo 'Building Infra/Accounting for Drift...'
                terraform apply\
                -var bucket_name=${prodBucket}\
                -var function_name=${functionName}\
                -var commit_id=${commitID()}\
                -auto-approve
               """ 
            }
        }

    	stage(‘Update_Version_NonProd’) {
    		when { 
                not { 
                    branch 'master' 
                }
            }	
    		steps {
              withAWS(role: 'JenkinsAssumedRole', roleAccount: nonprodAcct) {
                    
                    // sh "aws lambda update-function-code --function-name ${functionName} \
                    //     --s3-bucket ${nonprodBucket} \
                    //     --s3-key ${functionName}/${commitID()}.zip \
                    //     --region ${region}"
                    
             		sh "aws lambda publish-version --function-name ${functionName} \
             			--description '<https://github.com/keepitsts/${repoName}/commit/${commitID()}>'"          		
                }  
            } 
        }
        stage(‘Update_Version_Prod’) {
    		when { 
                branch 'master' 
            }
    		steps {
                withAWS(role: 'JenkinsAssumedRole', roleAccount: prodAcct) {
                    // sh "aws lambda update-function-code --function-name ${functionName} \
                    //     --s3-bucket ${prodBucket} \
                    //     --s3-key ${functionName}/${commitID()}.zip \
                    //     --region ${region}"
                    
                    sh "aws lambda publish-version --function-name ${functionName} \
             			--description '<https://github.com/keepitsts/${repoName}/commit/${commitID()}>'" 
                }
            } 
        }
    }
}

def commitID() {
    sh 'git rev-parse HEAD > .git/commitID'
    def commitID = readFile('.git/commitID').trim()
    sh 'rm .git/commitID'
    commitID
}