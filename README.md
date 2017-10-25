# Ansible AWS ElasticSearch module

For configuring/managing aws managed elasticsearch clusters

    ---

    - hosts: localhost
      tasks:
        - name: "Create ElasticSearch cluster"
          ec2_elasticsearch:
            name: "my-cluster"
            elasticsearch_version: "2.3"
            region: "us-west-1"
            instance_type: "m3.medium.elasticsearch"
            instance_count: 2
            dedicated_master: True
            zone_awareness: True
            dedicated_master_instance_type: "t2.micro.elasticsearch"
            dedicated_master_instance_count: 2
            ebs: True
            volume_type: "standard"
            volume_size: 10
            vpc_subnets: "subnet-e537d64a"
            vpc_security_groups: "sg-dd2f13cb"
            snapshot_hour: 13
            access_policies: "{{ lookup('file', 'cluster_policies.json') | from_json }}"
            profile: "myawsaccount"
          register: response

## VPC Configuration

### Endpoints

Non VPC clusters give endpoints at `DomainStatus.Endpoint`, however VPC clusters return it at `DomainStatus.Endpoints.vpc`

### Service Roles

AWS currently provides no way to create the correct service role for a vpc limited elasticsearch cluster. To
get the correct role configured in your account, create a test cluster in your vpc using the aws console. You can
delete it afterwards. If you don't have this, the module will fail with this error:

> Before you can proceed, you must enable a service-linked role to give Amazon ES permissions to access your VPC.

## Pitfalls

Access Policies may trigger continual updates if the format in `cluster_policies.json` differs from the AWS
returned value. To debug this, you can use the cli to get the policy back so you can compare or replace the contents
of your `cluster_policies.json` file.

`aws es describe-elasticsearch-domain --domain-name my-cluster --query DomainStatus.AccessPolicies --output text`
