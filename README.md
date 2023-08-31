# eks-factory
EKS Factory automates provisioning and configuration of EKS resources in a self-service manner.

## Introduction
EKS Factory is a solution for provisioning and managing EKS infrastructure (Cluster, Node Group etc.). It automates the resource creation and configuration of these resources in a self-service manner. At the core, we use CloudFormation to provision resources. We also leverage Lambda and CodeBuild to configure the provisioned resources.

> _Please read the article [EKS Factory](https://medium.com/p/372bce839d7/edit) to know more about the solution._

## Step-by-step Installation
Installation is a two-step process:

### STEP 1. Copy the solution source files in a S3 repository
EKS Factory uses nested CloudFormation stacks where parent stack references it's child stack templates stored in S3 bucket. So, we need to upload the templates along with other scripts in an S3 bucket.

```shell
aws s3 sync . s3://<S3 repository bucket/folder path>/ \
        --exclude ".git/*" --exclude ".gitignore" --exclude ".DS_Store" \
        --exclude "eks-factory.yaml" --exclude "install.sh" --exclude "README.md"
```

> _**Note:** CodeBuild requires source script files to be stored in S3 bucket within the same region, hence please make sure that the bucket is belonging to the same region where you are installing the solution._

#### Parameters
S3 repository: S3 repository bucket/folder path in the format: bucket/folder/sub-folder (without the slash at the begining/end).

### STEP 2. Creating Service Catalog portfolio and underlying products
EKS Factory offers catalog products under a portfolio. We create these using CloudFormation.

```shell
aws cloudformation create-stack \
        --stack-name EKS-Factory \
        --template-body file://eks-factory.yaml \
        --parameters ParameterKey=S3RepositoryPath,ParameterValue=<S3 repository bucket/folder path> \
                     ParameterKey=Owner,ParameterValue=<Owner details> \
                     ParameterKey=Users,ParameterValue=<End users> \
        --capabilities CAPABILITY_NAMED_IAM \
        --disable-rollback
```

#### Parameters
S3 repository: S3 repository bucket/folder path in the format: bucket/folder/sub-folder (without the slash at the begining/end). Bucket must belong to the same region where you are installing the solution.

Owner details: Owner name and/or email address.

End users: ARN of the IAM group/role.

## One-click Installation
The above installation steps are automated using Shell scripts.

```shell
sh install.sh <S3 repository bucket/folder path> <Owner details> <End users>
```

> _**Note:** This is the recommended step to install the solution unless you are insterested in any specific steps as mentioned above for troubleshooting or so. Please make sure that the bucket is belonging to the same region where you are installing the solution._

#### Parameters
S3 repository: S3 repository bucket/folder path in the format: bucket/folder/sub-folder (without the slash at the begining/end). Bucket must belong to the same region where you are installing the solution.

Owner details: Owner name and/or email address.

End users: ARN of the IAM group/role.

## Key Consideration before installation
Update the [aws-auth.yml.template](build-scripts/aws-auth.yml.template) based on your requirement. You need to add IAM users/roles that will have access to the provisioned clusters. Typically, these are the standard users/roles such as system administrators, audit users who would need to have access to all the resources. You can define different permission for different users/roles.


## Example Resource Provisioing
You can provision a whole infrastructure (an EKS Cluster with two Node Groups) using a simple yaml template like this:

```yaml
AWSTemplateFormatVersion: 2010-09-09
Description: Template to create an EKS Cluster and two Node Groups.

Resources:
  Cluster:
    Type: AWS::ServiceCatalog::CloudFormationProvisionedProduct
    Properties:
      ProductName: EKS Control Plane
      ProvisionedProductName: my-prod-EKS-Cluster
      ProvisioningArtifactName: New Cluster
      ProvisioningParameters:
      - Key: EnvironmentName
        Value: my-prod
      - Key: KubernetesVersion
        Value: "1.21"
      - Key: KmsKeyArn
        Value: <YOUR KMS KEY ARN>
      - Key: VpcId
        Value: <YOUR VPC ID>
      - Key: Subnets
        Value: "<YOUR SUBNET IDs SEPARATED BY COMMAS>"
      - Key: VpcCniVersion
        Value: v1.10.1-eksbuild.1
      - Key: CoreDnsVersion
        Value: v1.8.4-eksbuild.1
      - Key: KubeProxyVersion
        Value: v1.21.2-eksbuild.2
        
NodeGroup1:
    Type: AWS::ServiceCatalog::CloudFormationProvisionedProduct
    Properties:
      ProductName: EKS Data Plane
      ProvisionedProductName: my-prod-EKS-121-141-NodeGroup-1
      ProvisioningArtifactName: New Node Group
      ProvisioningParameters:
      - Key: EnvironmentName
        Value: my-prod
      - Key: KubernetesVersionNumber
        Value: 121
      - Key: BuildNumber
        Value: 141
      - Key: NodeGroupName
        Value: NodeGroup-1
      - Key: AmiId
        Value: <YOUR AMI ID>
      - Key: CapacityType
        Value: ON_DEMAND
      - Key: InstanceType
        Value: m5.2xlarge
      - Key: VolumeSize
        Value: 60
      - Key: VolumeType
        Value: gp3
      - Key: MinSize
        Value: 1
      - Key: MaxSize
        Value: 3
      - Key: DesiredSize
        Value: 3
      - Key: Subnets
        Value: "<YOUR SUBNET IDs SEPARATED BY COMMAS>"
      - Key: EnableCpuCfsQuota
        Value: "true"
      - Key: HttpTokenState
        Value: optional
    DependsOn:
    - Cluster
  
  NodeGroup2:
    Type: AWS::ServiceCatalog::CloudFormationProvisionedProduct
    Properties:
      ProductName: EKS Data Plane
      ProvisionedProductName: my-prod-EKS-121-141-NodeGroup-2
      ProvisioningArtifactName: New Node Group
      ProvisioningParameters:
      - Key: EnvironmentName
        Value: my-prod
      - Key: KubernetesVersionNumber
        Value: 121
      - Key: BuildNumber
        Value: 141
      - Key: NodeGroupName
        Value: NodeGroup-2
      - Key: AmiId
        Value: <YOUR AMI ID>
      - Key: CapacityType
        Value: ON_DEMAND
      - Key: InstanceType
        Value: m5.2xlarge
      - Key: KeyPair
        Value: <YOUR KEY PAIR NAME>
      - Key: VolumeSize
        Value: 60
      - Key: VolumeType
        Value: gp3
      - Key: MinSize
        Value: 1
      - Key: MaxSize
        Value: 3
      - Key: DesiredSize
        Value: 3
      - Key: Subnets
        Value: "<YOUR SUBNET IDs SEPARATED BY COMMAS>"
      - Key: EnableCpuCfsQuota
        Value: "true"
      - Key: HttpTokenState
        Value: optional
      - Key: TaintKey
        Value: <YOUR TAINT KEY>
      - Key: TaintValue
        Value: <YOUR TAINT VALUE>
      - Key: TaintEffect
        Value: <YOUR TAINT EFFECT>
      - Key: AdditionalLabels
        Value: "label1=value1,label2=value2"
      - Key: AdditionalTags
        Value: "tag1=value1,tag2=value2"
    DependsOn:
    - Cluster
```