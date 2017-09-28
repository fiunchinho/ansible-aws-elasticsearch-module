#!/usr/bin/python
# encoding: utf-8

# (c) 2015, Jose Armesto <jose@armesto.net>
#
# This file is part of Ansible
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = """
---
module: ec2_elasticsearch
short_description: Creates ElasticSearch cluster on Amazon
description:
  - It depends on boto3

version_added: "2.1"
author: "Jose Armesto (@fiunchinho)"
options:
  name:
    description:
      - Cluster name to be used.
    required: true
  elasticsearch_version:
    description:
      - Elasticsearch version to deploy. Default is '2.3'.
    required: false
  region:
    description:
      - The AWS region to use.
    required: true
    aliases: ['aws_region', 'ec2_region']
  instance_type:
    description:
      - Type of the instances to use for the cluster. Valid types are: 'm3.medium.elasticsearch'|'m3.large.elasticsearch'|'m3.xlarge.elasticsearch'|'m3.2xlarge.elasticsearch'|'t2.micro.elasticsearch'|'t2.small.elasticsearch'|'t2.medium.elasticsearch'|'r3.large.elasticsearch'|'r3.xlarge.elasticsearch'|'r3.2xlarge.elasticsearch'|'r3.4xlarge.elasticsearch'|'r3.8xlarge.elasticsearch'|'i2.xlarge.elasticsearch'|'i2.2xlarge.elasticsearch'
    required: true
  instance_count:
    description:
      - Number of instances for the cluster.
    required: true
  dedicated_master:
    description:
      - A boolean value to indicate whether a dedicated master node is enabled.
    required: true
  zone_awareness:
    description:
      - A boolean value to indicate whether zone awareness is enabled.
    required: true
  ebs:
    description:
      - Specifies whether EBS-based storage is enabled.
    required: true
  dedicated_master_instance_type:
    description:
      - The instance type for a dedicated master node.
    required: false
  dedicated_master_instance_count:
    description:
      - Total number of dedicated master nodes, active and on standby, for the cluster.
    required: false
  volume_type:
    description:
      - Specifies the volume type for EBS-based storage.
    required: true
  volume_size:
    description:
      - Integer to specify the size of an EBS volume.
    required: true
  snapshot_hour:
    description:
      - Integer value from 0 to 23 specifying when the service takes a daily automated snapshot of the specified Elasticsearch domain.
    required: true
  access_policies:
    description:
      - IAM access policy as a JSON-formatted string.
    required: true
  profile:
    description:
      - What Boto profile use to connect to AWS.
    required: false
requirements:
  - "python >= 2.6"
  - boto3
"""

EXAMPLES = '''

- ec2_elasticsearch:
    name: "my-cluster"
    elasticsearch_version: "2.3"
    region: "eu-west-1"
    instance_type: "m3.medium.elasticsearch"
    instance_count: 2
    dedicated_master: True
    zone_awareness: True
    dedicated_master_instance_type: "t2.micro.elasticsearch"
    dedicated_master_instance_count: 2
    ebs: True
    volume_type: "standard"
    volume_size: 10
    snapshot_hour: 13
    access_policies: "{{ lookup('file', 'files/cluster_policies.json') | from_json }}"
    profile: "myawsaccount"
'''
try:
    import botocore
    import boto3
    import json

    HAS_BOTO=True
except ImportError:
    HAS_BOTO=False

def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
            name = dict(required=True),
            instance_type = dict(required=True),
            instance_count = dict(required=True, type='int'),
            dedicated_master = dict(required=True, type='bool'),
            zone_awareness = dict(required=True, type='bool'),
            dedicated_master_instance_type = dict(),
            dedicated_master_instance_count = dict(type='int'),
            ebs = dict(required=True, type='bool'),
            volume_type = dict(required=True),
            volume_size = dict(required=True, type='int'),
            access_policies = dict(required=True, type='dict'),
            snapshot_hour = dict(required=True, type='int'),
            elasticsearch_version = dict(default='2.3'),
    ))

    module = AnsibleModule(
            argument_spec=argument_spec,
    )

    if not HAS_BOTO:
        module.fail_json(msg='boto3 required for this module, install via pip or your package manager')

    region, ec2_url, aws_connect_params = get_aws_connection_info(module, True)
    client = boto3_conn(module=module, conn_type='client', resource='es', region=region, **aws_connect_params)

    cluster_config = {
           'InstanceType': module.params.get('instance_type'),
           'InstanceCount': int(module.params.get('instance_count')),
           'DedicatedMasterEnabled': module.params.get('dedicated_master'),
           'ZoneAwarenessEnabled': module.params.get('zone_awareness')
    }

    ebs_options = {
           'EBSEnabled': module.params.get('ebs')
    }

    if cluster_config['DedicatedMasterEnabled']:
        cluster_config['DedicatedMasterType'] = module.params.get('dedicated_master_instance_type')
        cluster_config['DedicatedMasterCount'] = module.params.get('dedicated_master_instance_count')

    if ebs_options['EBSEnabled']:
        ebs_options['VolumeType'] = module.params.get('volume_type')
        ebs_options['VolumeSize'] = module.params.get('volume_size')

    snapshot_options = {
        'AutomatedSnapshotStartHour': module.params.get('snapshot_hour')
    }

    changed = False

    try:
        pdoc = json.dumps(module.params.get('access_policies'))
    except Exception as e:
        module.fail_json(msg='Failed to convert the policy into valid JSON: %s' % str(e))

    try:
        response = client.describe_elasticsearch_domain(DomainName=module.params.get('name'))
        status = response['DomainStatus']

        # Modify the provided policy to provide reliable changed detection
        policy_dict = module.params.get('access_policies')
        for statement in policy_dict['Statement']:
            if 'Resource' not in statement:
                # The ES APIs will implicitly set this
                statement['Resource'] = '%s/*' % status['ARN']
                pdoc = json.dumps(policy_dict)

        if status['ElasticsearchClusterConfig'] != cluster_config:
            changed = True

        if status['EBSOptions'] != ebs_options:
            changed = True

        if status['SnapshotOptions'] != snapshot_options:
            changed = True

        current_policy_dict = json.loads(status['AccessPolicies'])
        if current_policy_dict != policy_dict:
            changed = True

        if changed:
            response = client.update_elasticsearch_domain_config(
                    DomainName=module.params.get('name'),
                    ElasticsearchClusterConfig=cluster_config,
                    EBSOptions=ebs_options,
                    SnapshotOptions=snapshot_options,
                    AccessPolicies=pdoc,
            )

    except botocore.exceptions.ClientError as e:
        changed = True

        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            response = client.create_elasticsearch_domain(
                    DomainName=module.params.get('name'),
                    ElasticsearchVersion=module.params.get('elasticsearch_version'),
                    ElasticsearchClusterConfig=cluster_config,
                    EBSOptions=ebs_options,
                    SnapshotOptions=snapshot_options,
                    AccessPolicies=pdoc,
            )
        else:
            module.fail_json(msg='Error: %s' % str(e.response['Error']['Code']))

    module.exit_json(changed=changed, response=response)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
