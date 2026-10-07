from unittest.mock import Mock

from ec2_health_monitor.monitor import EC2HealthMonitor


def test_collect_marks_healthy_instance() -> None:
    ec2 = Mock()
    ec2.get_paginator.return_value.paginate.return_value = [
        {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-123",
                            "InstanceType": "t3.micro",
                            "State": {"Name": "running"},
                            "Placement": {"AvailabilityZone": "us-east-1a"},
                            "Tags": [{"Key": "Name", "Value": "web"}],
                        }
                    ]
                }
            ]
        }
    ]
    ec2.describe_instance_status.return_value = {
        "InstanceStatuses": [
            {
                "InstanceId": "i-123",
                "InstanceStatus": {"Status": "ok"},
                "SystemStatus": {"Status": "ok"},
            }
        ]
    }

    result = EC2HealthMonitor(ec2).collect()

    assert result[0].healthy is True
    assert result[0].name == "web"
    assert result[0].reason == "OK"


def test_collect_marks_stopped_instance_unhealthy() -> None:
    ec2 = Mock()
    ec2.get_paginator.return_value.paginate.return_value = [
        {"Reservations": [{"Instances": [{"InstanceId": "i-456", "State": {"Name": "stopped"}}]}]}
    ]
    ec2.describe_instance_status.return_value = {"InstanceStatuses": []}

    result = EC2HealthMonitor(ec2).collect()

    assert result[0].healthy is False
    assert "instance state is stopped" in result[0].reason
    assert "instance check is not-reported" in result[0].reason

