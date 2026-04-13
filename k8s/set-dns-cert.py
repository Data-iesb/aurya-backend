#!/usr/bin/env python3
"""Create Route53 CNAME for aurya.dataiesb.com pointing to the ALB created by the ingress."""

import boto3, json, sys, time

REGION = "us-east-1"
HOSTED_ZONE_ID = "Z05014761ROYBA3Z5YKY2"
DOMAIN = "aurya.dataiesb.com"
CERT_ARN = "arn:aws:acm:us-east-1:248189947068:certificate/77d012f4-6507-4af0-9af7-ce75e6a56e08"
NAMESPACE = "custom"
INGRESS_NAME = "aurya-ingress"

def get_alb_hostname():
    from kubernetes import client, config
    config.load_kube_config()
    v1 = client.NetworkingV1Api()
    ing = v1.read_namespaced_ingress(INGRESS_NAME, NAMESPACE)
    lb = ing.status.load_balancer.ingress
    if not lb:
        return None
    return lb[0].hostname

def get_alb_hosted_zone(alb_dns):
    elbv2 = boto3.client("elbv2", region_name=REGION)
    lbs = elbv2.describe_load_balancers()["LoadBalancers"]
    for lb in lbs:
        if lb["DNSName"] == alb_dns:
            return lb["CanonicalHostedZoneId"]
    return None

def upsert_dns(alb_dns, alb_zone_id):
    r53 = boto3.client("route53")
    change = {
        "Comment": "Aurya ALB alias",
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": DOMAIN,
                "Type": "A",
                "AliasTarget": {
                    "HostedZoneId": alb_zone_id,
                    "DNSName": f"dualstack.{alb_dns}",
                    "EvaluateTargetHealth": True,
                },
            },
        }],
    }
    resp = r53.change_resource_record_sets(HostedZoneId=HOSTED_ZONE_ID, ChangeBatch=change)
    return resp["ChangeInfo"]["Id"]

def main():
    print("⏳ Waiting for ALB hostname from ingress...")
    alb_dns = None
    for _ in range(30):
        alb_dns = get_alb_hostname()
        if alb_dns:
            break
        time.sleep(10)
    if not alb_dns:
        sys.exit("❌ ALB not ready after 5 min. Is the ingress applied?")

    print(f"✅ ALB: {alb_dns}")

    alb_zone_id = get_alb_hosted_zone(alb_dns)
    if not alb_zone_id:
        sys.exit(f"❌ Could not find ALB hosted zone for {alb_dns}")

    print(f"📝 Upserting Route53 A-alias: {DOMAIN} → {alb_dns}")
    change_id = upsert_dns(alb_dns, alb_zone_id)
    print(f"✅ Done! Change ID: {change_id}")
    print(f"\n🔒 Cert ARN (use in ingress): {CERT_ARN}")

if __name__ == "__main__":
    main()
