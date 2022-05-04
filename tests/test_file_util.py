from unittest.mock import MagicMock, call

from google.cloud import storage

from wdl_runner.file_util import gcs_cp


def test_gcs_cp():
    gcs_client = storage.Client()
    gcs_client.f_orig_bucket = gcs_client.bucket
    dest_bucketname = "bucket1"
    dest_url = f"gs://{dest_bucketname}/path1/path2/file2.txt"
    src_bucketname = "bucket2"

    buckets = {}
    actual_blobs = []

    def bucket(bucketname: str):
        res = gcs_client.f_orig_bucket(bucketname)
        if bucketname == dest_bucketname:
            dest_blob = res.blob("ignored1")
            dest_blob.upload_from_filename = MagicMock()
            res.blob = MagicMock(return_value=dest_blob)
            buckets[bucketname] = res
            actual_blobs.append(dest_blob)
            return res
        elif bucketname == src_bucketname:
            src_blob = res.blob("ignored2")
            actual_blobs.append(src_blob)
            res.copy_blob = MagicMock()
            res.blob = MagicMock(return_value=src_blob)
            buckets[bucketname] = res
            return res

    gcs_client.bucket = MagicMock(side_effect=bucket)

    gcs_cp(
        [
            f"gs://{src_bucketname}/path1/path2/file2.txt",
            "/some/local/file3.txt",
            "relative4.txt",
        ],
        dest_url,
        gcs_client,
    )

    gcs_client.bucket.assert_has_calls([call(dest_bucketname), call(src_bucketname)])
    assert len(actual_blobs) == 2
    actual_blobs[0].upload_from_filename.assert_has_calls(
        [call("/some/local/file3.txt"), call("relative4.txt")]
    )
    buckets[src_bucketname].copy_blob.assert_has_calls(
        [call(actual_blobs[1], buckets[dest_bucketname], "path1/path2/file2.txt")]
    )
