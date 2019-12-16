# fully managed elastic (scales for handling more data automatically) 
# service to load and deliver real-time data stream to S3 (object storage)

# gets records from Kinesis delivery stream
resource "aws_kinesis_firehose_delivery_stream" "firehose" {
	name = "horsing_around_kinesis_firehose"
	destination = "s3"
    
    kinesis_source_configuration = {
		kinesis_stream_arn = "${aws_kinesis_stream.stream.arn}"
		role_arn = "${aws_iam_role.firehose_role.arn}"
	} 
	
	s3_configuration {
		role_arn = "${aws_iam_role.firehose_role.arn}"
		bucket_arn = "${aws_s3_bucket.bucket.arn}"
		prefix = "web-data/raw/"
    }   
}