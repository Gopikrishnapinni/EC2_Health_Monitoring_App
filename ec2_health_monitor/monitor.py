from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class InstanceHealth:
    instance_id: str
    name: str
    state: str
    instance_type: str
    availability_zone: str
    instance_status: str
    system_status: str
    cpu_utilization: float | None
    healthy: bool
    reason: str
    checked_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tag_value(tags: Iterable[dict[str, str]] | None, key: str) -> str:
    for tag in tags or []:
        if tag.get("Key") == key:
            return tag.get("Value", "")
    return ""


class EC2HealthMonitor:
    def __init__(self, ec2_client: Any, cloudwatch_client: Any | None = None) -> None:
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client

    def collect(
        self,
        instance_ids: list[str] | None = None,
        cpu_threshold: float | None = None,
        lookback_minutes: int = 15,
    ) -> list[InstanceHealth]:
        instances = self._describe_instances(instance_ids)
        status_by_id = self._describe_status(instance_ids)
        checked_at = datetime.now(timezone.utc).isoformat()
        results: list[InstanceHealth] = []

        for instance in instances:
            instance_id = instance["InstanceId"]
            state = instance.get("State", {}).get("Name", "unknown")
            status = status_by_id.get(instance_id, {})
            instance_status = status.get("InstanceStatus", {}).get("Status", "not-reported")
            system_status = status.get("SystemStatus", {}).get("Status", "not-reported")
            cpu = self._cpu_utilization(instance_id, lookback_minutes)

            reasons: list[str] = []
            if state != "running":
                reasons.append(f"instance state is {state}")
            if instance_status != "ok":
                reasons.append(f"instance check is {instance_status}")
            if system_status != "ok":
                reasons.append(f"system check is {system_status}")
            if cpu_threshold is not None and cpu is not None and cpu > cpu_threshold:
                reasons.append(f"CPU {cpu:.1f}% exceeds {cpu_threshold:.1f}%")

            results.append(
                InstanceHealth(
                    instance_id=instance_id,
                    name=_tag_value(instance.get("Tags"), "Name") or "-",
                    state=state,
                    instance_type=instance.get("InstanceType", "unknown"),
                    availability_zone=instance.get("Placement", {}).get(
                        "AvailabilityZone", "unknown"
                    ),
                    instance_status=instance_status,
                    system_status=system_status,
                    cpu_utilization=cpu,
                    healthy=not reasons,
                    reason="; ".join(reasons) if reasons else "OK",
                    checked_at=checked_at,
                )
            )
        return results

    def _describe_instances(self, instance_ids: list[str] | None) -> list[dict[str, Any]]:
        paginator = self.ec2.get_paginator("describe_instances")
        params = {"InstanceIds": instance_ids} if instance_ids else {}
        instances: list[dict[str, Any]] = []
        for page in paginator.paginate(**params):
            for reservation in page.get("Reservations", []):
                instances.extend(reservation.get("Instances", []))
        return instances

    def _describe_status(self, instance_ids: list[str] | None) -> dict[str, dict[str, Any]]:
        params = {"IncludeAllInstances": True}
        if instance_ids:
            params["InstanceIds"] = instance_ids
        response = self.ec2.describe_instance_status(**params)
        return {
            item["InstanceId"]: item
            for item in response.get("InstanceStatuses", [])
            if "InstanceId" in item
        }

    def _cpu_utilization(self, instance_id: str, lookback_minutes: int) -> float | None:
        if self.cloudwatch is None:
            return None
        end = datetime.now(timezone.utc)
        response = self.cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=end - timedelta(minutes=lookback_minutes),
            EndTime=end,
            Period=300,
            Statistics=["Average"],
        )
        datapoints = response.get("Datapoints", [])
        if not datapoints:
            return None
        return float(max(datapoints, key=lambda point: point["Timestamp"])["Average"])

