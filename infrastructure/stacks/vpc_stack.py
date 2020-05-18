from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elb,
    core,
    )

class Vpc_stack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        alb_subnet = ec2.SubnetConfiguration(
            subnet_type=ec2.SubnetType.PUBLIC,
            name="ALB",
            cidr_mask=24
        )

        db_subnet = ec2.SubnetConfiguration(
            subnet_type=ec2.SubnetType.ISOLATED,
            name="DB",
            cidr_mask=24
        )

        # VPC
        vpc = ec2.Vpc(self, "VPC",
           max_azs=2,
           cidr="10.10.0.0/16",
           # configuration will create 2 groups in 2 AZs = 4 subnets.
           subnet_configuration=[alb_subnet, db_subnet],
           nat_gateway_provider=ec2.NatProvider.gateway(),
           nat_gateways=1,
           )
        # Security groups
        # Create Security group that allows traffic into the ALB
        alb_security_group = ec2.SecurityGroup(self, "ALBSecurityGroup",
           description="Ghost ALB Security Group",
           vpc=vpc
        )
        alb_security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "allow HTTP to ALB")
        alb_security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "allow HTTPS to ALB")

        # Create Security group for the host/ENI/Fargate that allows 2368
        fargate_security_group = ec2.SecurityGroup(self, "FargateSecurityGroup",
           description="Ghost ECS Fargate Security Group",
           vpc=vpc
        )
        fargate_security_group.add_ingress_rule(alb_security_group, ec2.Port.tcp(2368), "allow ghost default 2368 to fargate")

        # Create the DB's Security group which only allows access to memebers of the Ghost Fargate SG
        db_security_group = ec2.SecurityGroup(self, "DBSecurityGroup",
           description="Security group for RDS DB Instance for ghost cms",
           vpc=vpc
        )
        db_security_group.add_ingress_rule(fargate_security_group, ec2.Port.tcp(3306), "allow ghost fargate host to connect to db")

        ghost_alb = elb.ApplicationLoadBalancer(self, "GhostALB",
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=alb_security_group,
            vpc=vpc
        )

        ghost_target_health_check = elb.HealthCheck(
            interval=core.Duration.seconds(30),
            protocol=elb.Protocol.HTTP,
            timeout=core.Duration.seconds(10),
            healthy_threshold_count=4,
            unhealthy_threshold_count=3,
            healthy_http_codes="200,301"
        )

        ghost_target_group = elb.ApplicationTargetGroup(self, "GhostTargetGroup",
            port=2368,
            protocol=elb.Protocol.HTTP,
            vpc=vpc,
            health_check=ghost_target_health_check,
            target_type=elb.TargetType.IP
        )

        ghost_alb_listener = elb.ApplicationListener(self, "Listener80",
            port=80,
            protocol=elb.Protocol.HTTP,
            load_balancer=ghost_alb,
            default_target_groups=[ghost_target_group]
        )


        core.CfnOutput(self, "vpcid", value=vpc.vpc_id)
        core.CfnOutput(self, "alb_url", description="ALB URL", value=ghost_alb.load_balancer_dns_name)

        self.output_props = props.copy()
        self.output_props['vpc'] = vpc
        self.output_props['subnets'] = vpc.public_subnets
        self.output_props['alb_security_group'] = alb_security_group
        self.output_props['fargate_security_group'] = fargate_security_group
        self.output_props['db_security_group'] = db_security_group

    @property
    def outputs(self):
        return self.output_props
