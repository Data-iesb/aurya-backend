#!/usr/bin/env python3
"""Create Route53 A-alias for api.dataiesb.com → nginx NLB (same as trino.dataiesb.com)."""

import boto3

HOSTED_ZONE_ID = "Z05014761ROYBA3Z5YKY2"
DOMAIN = "api.dataiesb.com"

# Nginx ingress NLB (shared with trino, langfuse, etc.)
NLB_DNS = "k8s-ingressn-ingressn-26ad48bc1e-a729d9f68905afd6.elb.us-east-1.amazonaws.com"
NLB_HOSTED_ZONE_ID = "Z26RNL4JYFTOTI"

r53 = boto3.client("route53")

resp = r53.change_resource_record_sets(
    HostedZoneId=HOSTED_ZONE_ID,
    ChangeBatch={
        "Comment": "Aurya API backend",
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": DOMAIN,
                "Type": "A",
                "AliasTarget": {
                    "HostedZoneId": NLB_HOSTED_ZONE_ID,
                    "DNSName": NLB_DNS,
                    "EvaluateTargetHealth": True,
                },
            },
        }],
    },
)

print(f"✅ {DOMAIN} → {NLB_DNS}")
print(f"   Change ID: {resp['ChangeInfo']['Id']}")
