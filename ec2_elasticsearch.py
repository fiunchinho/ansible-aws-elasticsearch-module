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
    required: true
  dedicated_master_instance_count:
    description:
      - Total number of dedicated master nodes, active and on standby, for the cluster.
    required: true
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
  aws_access_key:
    description:
      - AWS access key to sign the requests.
    required: true
    aliases: ['aws_access_key', 'ec2_access_key']
  aws_secret_key:
    description:
      - AWS secret key to sign the requests.
    required: true
    aliases: ['aws_secret_key', 'ec2_secret_key']
requirements:
  - "python >= 2.6"
  - boto3
"""

EXAMPLES = '''

- ec2_elasticsearch:
    name: "my-cluster"
    region: "eu-west-1"
    aws_access_key: "AKIAJ5CC6CARRKOX5V7Q"
    aws_secret_key: "cfDKFSXEo1CC6gfhfhCARRKOX5V7Q"
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
'''
try:
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
            instance_count = dict(required=True),
            dedicated_master = dict(required=True),
            zone_awareness = dict(required=True),
            dedicated_master_instance_type = dict(required=True),
            dedicated_master_instance_count = dict(required=True),
            ebs = dict(required=True),
            volume_type = dict(required=True),
            volume_size = dict(required=True),
            access_policies = dict(required=True),
            snapshot_hour = dict(required=True),
    ))

    module = AnsibleModule(
            argument_spec=argument_spec,
    )

    if not HAS_BOTO:
        module.fail_json(msg='boto3 required for this module, install via pip or your package manager')

    try:
        # boto3.setup_default_session(profile_name=module.params.get('profile'))
        client = boto3.client(service_name='es', region_name=module.params.get('region'), aws_access_key_id=module.params.get('aws_access_key'), aws_secret_access_key=module.params.get('aws_secret_key'))
    except (boto.exception.NoAuthHandlerFound, StandardError), e:
        module.fail_json(msg=str(e))

    try:
        pdoc = json.dumps(module.params.get('access_policies'))
    except Exception as e:
        module.fail_json(msg='Failed to convert the policy into valid JSON: %s' % str(e))

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
        cluster_config['DedicatedMasterCount'] = int(module.params.get('dedicated_master_instance_count')

    if ebs_options['EBSEnabled']:
        ebs_options['VolumeType'] = module.params.get('volume_type')
        ebs_options['VolumeSize'] = int(module.params.get('volume_size'))

    response = client.create_elasticsearch_domain(
            DomainName=module.params.get('name'),
            ElasticsearchClusterConfig=cluster_config,
            EBSOptions=ebs_options,
            SnapshotOptions={
                'AutomatedSnapshotStartHour': module.params.get('snapshot_hour')
            }
    )

    response_update = client.update_elasticsearch_domain_config(
            DomainName=module.params.get('name'),
            AccessPolicies=pdoc
    )
    module.exit_json(changed=True, response=response, policies=response_update["DomainConfig"]["AccessPolicies"]["Options"])

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
