from unittest.mock import patch

from wdl_runner.cromwell_driver import CromwellDriver


def test_cromwell_driver_start():
    subject = CromwellDriver(
        cromwell_conf="cromwell.conf",
        cromwell_jar="cromwell.jar",
        jvm_flags=["-Xmx8G", "-Dprop=val"],
    )
    with patch("subprocess.Popen") as popen_mock:
        popen_mock.return_value = "assigned"
        subject.start()
        popen_mock.assert_called_once_with(
            [
                "java",
                "-Dconfig.file=cromwell.conf",
                "-Xmx8G",
                "-Dprop=val",
                "-jar",
                "cromwell.jar",
                "server",
            ]
        )
