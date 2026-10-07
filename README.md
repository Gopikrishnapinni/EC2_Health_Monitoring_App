# EC2 Health Monitoring Tool

A small Python CLI for checking AWS EC2 instance health. It reports:

- Instance state (`running`, `stopped`, etc.)
- EC2 instance and system status checks
- Availability zone and instance type
- Optional recent average CPU utilization from CloudWatch
- A process-friendly exit code (`0` when all instances are healthy, `1` otherwise)

## Requirements

- Python 3.10+
- AWS credentials configured through the standard boto3 chain
- IAM permissions: `ec2:DescribeInstances`, `ec2:DescribeInstanceStatus`
- Optional CPU check: `cloudwatch:GetMetricStatistics`

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Usage

Check every instance visible in the configured region:

```powershell
ec2-health --region us-east-1
```

Check specific instances and include a CPU threshold:

```powershell
ec2-health --region us-east-1 --instance-id i-0123456789abcdef0 --cpu-threshold 80
```

Produce JSON for automation:

```powershell
ec2-health --region us-east-1 --json
```

The region can also come from `AWS_DEFAULT_REGION` or the AWS CLI profile configuration.

## Tests

```powershell
python -m pytest
```

## Docker

Build and run the monitor with AWS credentials supplied by your local environment:

```powershell
docker build -t ec2-health-monitor:latest .
docker run --rm `
  -e AWS_DEFAULT_REGION=us-east-1 `
  -e AWS_ACCESS_KEY_ID `
  -e AWS_SECRET_ACCESS_KEY `
  -e AWS_SESSION_TOKEN `
  ec2-health-monitor:latest
```

The optional Docker Compose setup runs one check and exits:

```powershell
$env:AWS_DEFAULT_REGION = "us-east-1"
docker compose run --rm ec2-health-monitor
```

## Kubernetes

The Kubernetes files define a CronJob that runs every five minutes. The
container uses an Amazon EKS service account with IRSA, so long-lived AWS
access keys are not stored in Kubernetes.

Before applying, update these placeholders:

1. Replace the IAM role ARN in `k8s/serviceaccount.yaml`.
2. Set the region and CPU threshold in `k8s/configmap.yaml`.
3. Change the image registry and tag in `k8s/kustomization.yaml`.

Build and publish the image, then deploy:

```powershell
docker build -t your-registry.example.com/ec2-health-monitor:0.1.0 .
docker push your-registry.example.com/ec2-health-monitor:0.1.0
kubectl apply -k k8s
kubectl -n ec2-monitor get cronjobs
kubectl -n ec2-monitor get jobs
kubectl -n ec2-monitor logs -l app.kubernetes.io/name=ec2-health-monitor
```

The IAM role used by the service account needs:

- `ec2:DescribeInstances`
- `ec2:DescribeInstanceStatus`
- `cloudwatch:GetMetricStatistics`
