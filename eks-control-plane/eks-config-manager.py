import boto3
import logging
from botocore.exceptions import ClientError
import os
import json
import time
import cfnresponse
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
eks = boto3.client('eks')
iam = boto3.client('iam')
codebuild = boto3.client('codebuild')
autoscaling = boto3.client('autoscaling')

def patch_coredns_to_work_on_fargate(event, context):
  if event['RequestType'] == 'Create':
    logger.info('Applying CoreDNS patch to work on fargate...')
    command = 'patch-coredns-create'
    args = ''
  
  elif event['RequestType'] == 'Delete':
    logger.info('Removing CoreDNS patch to work on fargate...')
    command = 'patch-coredns-delete'
    args = ''

  elif event['RequestType'] == 'Update':
    return 'Request skipped.'

  environment_name = os.getenv('ENVIRONMENT_NAME')

  while True:
    try:
      response = codebuild.start_build(projectName = environment_name + '-EKS-ConfigMapManager', 
                        environmentVariablesOverride = [
                          {
                            'name': 'CLUSTER_NAME',
                            'value': os.getenv('CLUSTER_NAME'),
                            'type': 'PLAINTEXT'
                          },
                          {
                            'name': 'COMMAND',
                            'value': command,
                            'type': 'PLAINTEXT'
                          },
                          {
                            'name': 'ARGUMENTS',
                            'value': args,
                            'type': 'PLAINTEXT'
                          }],
                        timeoutInMinutesOverride = 5)
      break
    except ClientError as e:
      if e.response['Error']['Code'] == 'AccountLimitExceededException':
        logger.info('Waiting for last build to finish...')
        time.sleep(10)
      else:
        raise
                        
  logger.info('Build started.')
                  
  while True:
    status = codebuild.batch_get_builds(ids = [response['build']['id']])['builds'][0]['buildStatus']

    if status == 'SUCCEEDED':
      return 'Patch CoreDNS deployment to work on Fargate applied.'
    elif status == 'IN_PROGRESS':
      logger.info('Waiting for build to finish...')
      time.sleep(10)
    else:
      raise Exception('Build ' + status + '.')

def update_eks_cluster_logging(event, context):
  if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
    logger.info('Applying logging configuration...')
        
    eks.update_cluster_config(name = os.getenv('CLUSTER_NAME'), 
                              logging = { 'clusterLogging': [{'types': [log], 'enabled': (status == 'enabled')} for log, status in (tuple(logging.split('=')) for logging in event['ResourceProperties']['ClusterLogging'].split(','))]})

    return 'Logging configuration applied.'

  elif event['RequestType'] == 'Delete':
    return 'Request skipped.'

def update_config_map(event, context, node_iam_role_arn):
  if node_iam_role_arn:
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
      command = 'add-role'
      logger.info('Adding Node IAM Role \'' + node_iam_role_arn + '\' to ConfigMap...')
    elif event['RequestType'] == 'Delete':
      command = 'delete-role'
      logger.info('Deleting Node IAM Role \'' + node_iam_role_arn + '\' from ConfigMap...')

    args = node_iam_role_arn

  else:
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
      account_id = context.invoked_function_arn.split(":")[4]
      command = 'initialize-config-map'
      args = account_id
      logger.info('Initializing ConfigMap...')
    
    elif event['RequestType'] == 'Delete':
      return 'Request skipped.'

  environment_name = os.getenv('ENVIRONMENT_NAME')

  while True:
    try:
      response = codebuild.start_build(projectName = environment_name + '-EKS-ConfigMapManager', 
                        environmentVariablesOverride = [
                          {
                            'name': 'CLUSTER_NAME',
                            'value': os.getenv('CLUSTER_NAME'),
                            'type': 'PLAINTEXT'
                          },
                          {
                            'name': 'COMMAND',
                            'value': command,
                            'type': 'PLAINTEXT'
                          },
                          {
                            'name': 'ARGUMENTS',
                            'value': args,
                            'type': 'PLAINTEXT'
                          }],
                        timeoutInMinutesOverride = 5)
      break
    except ClientError as e:
      if e.response['Error']['Code'] == 'AccountLimitExceededException':
        logger.info('Waiting for last build to finish...')
        time.sleep(10)
      else:
        raise
                        
  logger.info('Build started.')
                  
  while True:
    status = codebuild.batch_get_builds(ids = [response['build']['id']])['builds'][0]['buildStatus']

    if status == 'SUCCEEDED':
      return 'ConfigMap updated.'
    elif status == 'IN_PROGRESS':
      logger.info('Waiting for build to finish...')
      time.sleep(10)
    else:
      raise Exception('Build ' + status + '.')

def add_additional_labels(event, context):
  if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
    nodegroup_name = os.getenv('ENVIRONMENT_NAME') + '-EKS-' + event['ResourceProperties']['KubernetesVersionNumber'] + '-'+ event['ResourceProperties']['BuildNumber'] + '-' + event['ResourceProperties']['NodeGroupName']

    logger.info('Adding additional Kubernetes labels to the NodeGroup \'' + nodegroup_name + '\'...')

    eks.update_nodegroup_config(clusterName = os.getenv('CLUSTER_NAME'), 
                                nodegroupName = nodegroup_name,
                                labels = {
                                  'addOrUpdateLabels': [{k: v for k, v in ([tuple(label.split('=')) for label in event['ResourceProperties']['AdditionalLabels'].split(',')])}][0]
                                })

    return 'Additional labels added.'

  elif event['RequestType'] == 'Delete':
    return 'Request skipped.'

def add_additional_tags(event, context):
  if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
    nodegroup_name = os.getenv('ENVIRONMENT_NAME') + '-EKS-' + event['ResourceProperties']['KubernetesVersionNumber'] + '-'+ event['ResourceProperties']['BuildNumber'] + '-' + event['ResourceProperties']['NodeGroupName']
    
    asg_name = eks.describe_nodegroup(clusterName = os.getenv('CLUSTER_NAME'), 
                                      nodegroupName = nodegroup_name)['nodegroup']['resources']['autoScalingGroups'][0]['name']

    logger.info('Adding additional tags to underlying Auto Scaling Group \'' + asg_name + '\'...')
    
    autoscaling.create_or_update_tags(Tags=[{'ResourceId': asg_name, 'ResourceType': 'auto-scaling-group', 'Key': k, 'Value': v, 'PropagateAtLaunch': True} for k, v in (tuple(label.split('=')) for label in event['ResourceProperties']['AdditionalTags'].split(','))])

    logger.info('Adding additional tags to existing Nodes under Auto Scaling Group \'' + asg_name + '\'...')

    ec2.create_tags(Resources=[instance['InstanceId'] for instance in autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])['AutoScalingGroups'][0]['Instances']],
                    Tags=[{'Key': k, 'Value': v} for k, v in (tuple(label.split('=')) for label in event['ResourceProperties']['AdditionalTags'].split(','))])

    return 'Additional tags added.'

  elif event['RequestType'] == 'Delete':
    return 'Request skipped.'

def process_custom_resource_response(event, context):
  response = {}

  try:
    if event['RequestType'] not in ['Create', 'Update', 'Delete'] or 'ResourceProperties' not in event:
      raise Exception('Unknown event.')

    if 'ClusterLogging' in event['ResourceProperties']:
      response['Response'] = update_eks_cluster_logging(event, context)
        
    elif 'NodeIamRoleArn' in event['ResourceProperties']:
      response['Response'] = update_config_map(event, context, node_iam_role_arn = event['ResourceProperties']['NodeIamRoleArn'])

    elif 'AdditionalLabels' in event['ResourceProperties']:
      response['Response'] = add_additional_labels(event, context)

    elif 'AdditionalTags' in event['ResourceProperties']:
      response['Response'] = add_additional_tags(event, context)

    elif 'PatchCoreDnsToWorkOnFargate' in event['ResourceProperties']:
      response['Response'] = patch_coredns_to_work_on_fargate(event, context)

    else:
      raise Exception('Unknown event.')

    cfnresponse.send(event, context, cfnresponse.SUCCESS, response)
      
  except Exception as e:
    logger.error(str(e))
    response['Response'] = ((response['Response'] + '\n') if 'Response' in response else '') + str(e)
    cfnresponse.send(event, context, cfnresponse.FAILED, response)

def lambda_handler(event, context):
  logger.info("REQUEST RECEIVED:\n" + str(event))

  if 'RequestType' in event:
    return process_custom_resource_response(event, context)

  else:
    logger.error('Unknown event.')
    
