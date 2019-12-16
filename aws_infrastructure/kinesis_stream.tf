# this stream continually captures and stores data for up to 24 hours
resource "aws_kinesis_stream" "stream" {
	name = "horsing_around_kinesis_stream"
	shard_count = 1
}