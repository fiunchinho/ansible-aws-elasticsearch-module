# Ansible AWS ElasticSearch module

Adapted from fiunchinho.ansible-aws-elasticsearch-module. This repo
shifts it into a role for ansible galaxy.

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
            snapshot_hour: 13
            access_policies: "{{ lookup('file', 'cluster_policies.json') | from_json }}"
            profile: "myawsaccount"
          register: response


