#!/bin/bash

if [[ $# -eq 0 ]] ; then
    echo 'Please enter your bucket name as ./setup_infra.sh your-bucket'
    exit 0
fi


AWS_ID=$(aws sts get-caller-identity --query Account --output text | cat)
AWS_REGION=$(aws configure get region)

SERVICE_NAME=batch-house-sale
IAM_ROLE_NAME=spectrum-redshift

REDSHIFT_USER=user1
REDSHIFT_PASSWORD=*****
REDSHIFT_PORT=5439


echo "Creating bucket "$1""
aws s3api create-bucket --acl public-read-write --bucket $1 --output text >> setup.log

echo "move data to S3"
aws s3 cp s3://main-landing-bucket/data.zip ./
unzip data.zip

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

aws iam attach-role-policy --role-name $IAM_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess --output text >> setup.log
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

psql -f ./redshift_setup.sql postgres://$REDSHIFT_USER:$REDSHIFT_PASSWORD@$REDSHIFT_HOST:$REDSHIFT_PORT/dev
rm ./redshift_setup.sql

