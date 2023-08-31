if [ $# -eq 3 ]; then

    echo '*** Copying source files to S3 repository ***'
    aws s3 sync . s3://$1/ \
        --exclude ".git/*" --exclude ".gitignore" --exclude ".DS_Store" \
        --exclude "eks-factory.yaml" --exclude "install.sh" --exclude "README.md"

    echo '*** Creating Service Catalog portfolio and underlying products ***'
    aws cloudformation create-stack \
        --stack-name EKS-Factory \
        --template-body file://eks-factory.yaml \
        --parameters ParameterKey=S3RepositoryPath,ParameterValue=$1 \
                     ParameterKey=Owner,ParameterValue=$2 \
                     ParameterKey=Users,ParameterValue=$3 \
        --capabilities CAPABILITY_NAMED_IAM \
        --disable-rollback

else
    echo
    echo "\tUsage: sh $0 <S3 repository bucket/folder path> <Owner details> <End users>"
    echo
    echo "\tParameters:"
    echo "\t\t1. S3 repository path in the format: bucket/folder/sub-folder (without the slash at the begining/end)."
    echo "\t\t   Bucket must belong to the same region where you are installing the solution."
    echo "\t\t2. Owner of the portfolio and products."
    echo "\t\t3. ARN of the IAM user/group/role who can use the products."
    echo
fi