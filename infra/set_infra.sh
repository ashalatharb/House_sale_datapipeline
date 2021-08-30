#!/bin/bash

AWS_ID=$(aws sts get-caller-identity --query Account --output text | cat)
AWS_REGION=$(aws configure get region)

LANDING_BUCKET = main-landing-zone # bucket name for raw data store
STAGING_BUCKET = main-staging-area # bucket name for staging data before target read

echo "Creating landing bucket "
aws s3api create-bucket --acl public-read-write --bucket STAGING_BUCKET --output text >> setup.log

echo "move data to S3"
aws s3 cp s3://main-landing-zone/ ./Data/kc_house_data.csv.zip
unzip kc_house_data.zip


echo "Creating staging bucket "
aws s3api create-bucket --bucket main-staging-area --output text >> setup.log

echo "redshift setup"

REDSHIFT_USER=redshift_user
REDSHIFT_PASSWORD=Redshift_user123
REDSHIFT_PORT=5439

echo '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "redshift.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}' > ./trust-policy.json


echo "Creating AWS IAM role"
aws iam create-role --role-name $IAM_ROLE_NAME --assume-role-policy-document file://trust-policy.json --description 'spectrum access for redshift' >> setup.log

echo "Attaching AmazonS3ReadOnlyAccess Policy to our IAM role"
aws iam attach-role-policy --role-name $IAM_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess --output text >> setup.log
echo "Attaching AWSGlueConsoleFullAccess Policy to our IAM role"
aws iam attach-role-policy --role-name $IAM_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess --output text >> setup.log

echo "Creating an AWS Redshift Cluster named "$SERVICE_NAME""
aws redshift create-cluster --cluster-identifier $SERVICE_NAME --node-type dc2.large --master-username $REDSHIFT_USER --master-user-password $REDSHIFT_PASSWORD --cluster-type single-node --publicly-accessible --iam-roles "arn:aws:iam::"$AWS_ID":role/"$IAM_ROLE_NAME"" >> setup.log


while :
do
   echo "Waiting for Redshift cluster "$SERVICE_NAME" to start, sleeping for 60s before next check"
   sleep 60
   REDSHIFT_CLUSTER_STATUS=$(aws redshift describe-clusters --cluster-identifier $SERVICE_NAME --query 'Clusters[0].ClusterStatus' --output text)
   if [[ "$REDSHIFT_CLUSTER_STATUS" == "available" ]]
   then
	break
   fi
done

REDSHIFT_HOST=$(aws redshift describe-clusters --cluster-identifier $SERVICE_NAME --query 'Clusters[0].Endpoint.Address' --output text)


echo "Successfully complted all the setup"
