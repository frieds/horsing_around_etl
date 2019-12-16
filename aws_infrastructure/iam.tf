resource "aws_iam_role" "segment_events_role" {
  name = "segment-events-role"
  description = "Allows Segment permission to write to a Kinesis stream"

  assume_role_policy = <<EOF
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": "sts:AssumeRole",
			"Principal": {
				"AWS": "arn:aws:iam::595280932656:root",
				"Service": "kinesis.amazonaws.com"
			}
		}
	]
}
EOF
}


resource "aws_iam_policy" "kinesis_stream_write_policy" {
  name = "kinesis-stream-write-policy"
  description = "Policy allowing put records and read records to Kinesis stream"

  policy = <<EOF
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": [
				"kinesis:*"
			],
			
			"Resource": [
				"${aws_kinesis_stream.stream.arn}"
			]
		}
	]
}
EOF
}

# gives segment_events_role permission to write to Kinesis stream using policy
resource "aws_iam_role_policy_attachment" "segment_policy_attachment_kinesis" {
  role       = "${aws_iam_role.segment_events_role.name}"
  policy_arn = "${aws_iam_policy.kinesis_stream_write_policy.arn}"
}

resource "aws_iam_role" "firehose_role" {
  name = "firehose-role"
  description = "Creates role to write to Firehose"

  assume_role_policy = <<EOF
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": "sts:AssumeRole",
			"Principal": {
				"Service": "firehose.amazonaws.com"
			}
		}
	]
}
EOF
}

resource "aws_iam_policy" "kinesis_firehose_policy" {
  name = "kinesis-firehose-policy"
  description = "Policy allows loading streaming data into S3"
  policy = <<EOF
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": [
				"s3:*"
			],
			"Resource": [
				"${aws_s3_bucket.bucket.arn}",
				"${aws_s3_bucket.bucket.arn}/*"		
				]
		},
		{
			"Effect": "Allow",
			"Action": [
				"kinesis:*"
			],
			"Resource": [
				"${aws_kinesis_stream.stream.arn}"	
				]
		}
	]
}
EOF
}


# # gives role to firehose permissions to send data to s3 destination
resource "aws_iam_role_policy_attachment" "kinesis_policy_attachment_s3" {
  role       = "${aws_iam_role.firehose_role.name}"
  policy_arn = "${aws_iam_policy.kinesis_firehose_policy.arn}"
}


## If you don't already have a policy, uncomment this section
#resource "aws_iam_role_policy" "my_s3_policy" {
#  name = "my_s3_policy"
#  role = "${aws_iam_role.glue.id}"
#  policy = <<EOF
#{
#  "Version": "2012-10-17",
#  "Statement": [
#    {
#      "Effect": "Allow",
#      "Action": [
#        "s3:*"
#      ],
#      "Resource": [
#        "arn:aws:s3:::my_bucket",
#        "arn:aws:s3:::my_bucket/*"
#      ]
#    }
#  ]
#}
#EOF
#}