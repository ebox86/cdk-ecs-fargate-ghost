#!/usr/bin/env python3

from aws_cdk import core

from stacks.vpc_stack import Vpc_stack
from stacks.rds_stack import Rds_stack
from stacks.pipeline_stack import Pipeline_stack
from stacks.fargate_stack import Fargate_stack

props = {
            "namespace": "ghost-cms",
            "github-owner": "ebox86",
            "github-repository" : "cdk-ecs-fargate-ghost"
        }
app = core.App()

vpc = Vpc_stack(app, "ghost-vpc", props)
rds = Rds_stack(app, "ghost-rds", vpc.outputs)
rds.add_dependency(vpc)
pipeline = Pipeline_stack(app, "ghost-pipeline", vpc.outputs)
pipeline.add_dependency(rds)
fargate = Fargate_stack(app, "ghost-fargate", pipeline.outputs)
fargate.add_dependency(pipeline)

app.synth()
