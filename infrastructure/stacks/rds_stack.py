from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    core
    )

class Rds_stack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Aurora RDS Cluster
        db_Aurora_cluster = rds.DatabaseCluster(self, "ghost_db_cluster",
            default_database_name=f"{props['namespace']}-db",
            engine=rds.DatabaseClusterEngine.AURORA_MYSQL,
            engine_version="5.7.12",
            master_user=rds.Login(username="admin"),
            instance_props=rds.InstanceProps(
                vpc=props['vpc'],
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.ISOLATED),
                security_group=props['db_security_group'],
                instance_type=ec2.InstanceType(instance_type_identifier="t2.small")
            ),
            instances=2,
            parameter_group=rds.ClusterParameterGroup.from_parameter_group_name(
                self, "para-group-aurora",
                parameter_group_name="default.aurora-mysql5.7"
            ),
        )
