# Project Overview: 1-minute Read

I built this project because I wanted to learn the basics of an optimal toolset for ETL to extract data from a web app, do transformations and upload to a data store. I picked this process because it can *generally* dynamically scale with more data, is cost-efficient, modular (easy to integrate various analytics or db solutions later) and are common tools of data engineers. Therefore, I chose Airflow, the AWS stack, Python, Docker and Terraform. In this project, I use small data. However, I got experience setting up the basics of infrastructure and syntax of these tools so I would feel confident to get this process up-and-running for a large data project.

The code/stack: Flask App that's a mini Twitter clone → [Segment](https://segment.com/) event tracking → AWS Kinesis stream → AWS Firehose → AWS S3 raw objects collected with prefix `web-data/raw` as raw data (allows flexibility to use this store for any type of later analysis) → transform raw data into relational db tables using Airflow in a Docker image running locally → send AWS transformed objects to S3 with prefix `web-data/transformed` → AWS Glue to define schema (aka Data Catalog) to use for Athena → AWS Athena (serverless db) → AWS Quicksight (dashboard tool)

# Project Overview: 5-Minute Read (Slightly Detailed)

## Flask App

Code is not included in this repo.

I followed the Flask [mega tutorial series](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) by Miguel Grinberg. I built a simplified Twitter clone that allows visitors to register, login, create posts, create a profile page, follow users and a few more features. App is hosted on Heroku. The Postgres db hosted with Heroku is not used for the ETL pipeline or analysis. App is at: [https://horsing-around.herokuapp.com/register](https://horsing-around.herokuapp.com/register)

I used Segment for event tracking of just a few actions. 

## Instantiate Infrastructure Resources

Terraform files to create IAM policy, S3 bucket, Kinesis stream, Firehose, policies and attach proper roles and policies to these services.

## ETL pipeline

There are three Python scripts and a CSV. This part is in transition. Previously, I had a cron job running on my local machine every 2 minutes that would kick off a Python script called  `s3_transformations.py` and use a library in  `s3_data_class.py`. I also record each time the cron job is run in a CSV titled `cron_logs.csv`. The scripts read in data from S3 with prefix `web-data/raw` and checks the `last_modified` attribute of the S3 object. We compare the `last_modified` value with the last time the cron job was run. If the last modified is greater than the last time the cron job was run, we perform transformations on the data and upload it back to s3. The transformations: decode it from bytes to a string object and cast it to a dictionary. Script can read in one or many objects with each cron run. This dictionary has several event types (post created, follow user, unfollow user, about user profile change) and all attributes relevant for all events. I use pandas to create a dataframe of records for each event type and event-relevant attributes. I then compress the dataframe into Parquet file format and upload back to S3 under the prefix `web-data/transformed`.

**In progress:** moving my Python scripts to this Docker image running locally [https://github.com/puckel/docker-airflow](https://github.com/puckel/docker-airflow) so I can use Airflow instead of a cron job. Also utilized this command to run `docker-compose docker-compose.yml up -d` to create new services in containers specified in the yml file. Redis and Postgres are useful for the CeleryExecutor and would allow for Airflow to be run with a CeleryExecutor so tasks could be run in parallel. Other services are Airflow, a webserver and a scheduler. A DAG specifies to run the same python scripts mentioned above every 2 minutes. AWS credentials are read through a mounted volume to direct to the config file on my local machine.

I then setup AWS Glue to read from the `web-data/transformed` prefix and it infers these db tables of `follows`, `posts`, `unfollows` and `users`. I then have Amazon Athena query from the Glue inferred schema and can connect Athena db to any data-viz tool.

## Analysis-ready

Connect Athena DB to Amazon Quicksight dashboard tool. Write SQL queries and use drag-and-drop editor for insights.

# Next Steps for the Project

- better understand what happens when you pull a docker image (I may need to re-pull with a requirements.txt in the repo so pip packages are automatically installed; I think all services created use the same base packages; need `boto3` and `pyarrow` installed)
- Setup CeleryExecutor YAML file with `docker-compose up` command
- ensure pycache folders aren't automatically created
- ensure example dags aren't loaded and don't appear with `airflow list_dags`
- set new start date for dag slightly in the future
- verify dag is running
    - check docker services are running
    - check Airflow UI
    - run airflow `list_dags`
    - check dag logs
    - see if s3 has new transformation objects for today's date
- add more inline comments to etl scripts
- Use static type checker for Python [http://mypy-lang.org/](http://mypy-lang.org/) (function_with_pep484_type_annotations)
- Build great documentation [http://www.sphinx-doc.org/en/master/](http://www.sphinx-doc.org/en/master/)
- Implement pre-commit hooks: [https://pre-commit.com/](https://pre-commit.com/) 
- Implement Python code formatter [https://black.readthedocs.io/en/stable/](https://black.readthedocs.io/en/stable/)
- put important credentials into environment variables and read them into Terraform config
- Set up Terraform workspaces (every dev has their own staging and environment; file in S3 has terraform state for each dev to use)
- Design fact tables in my pipeline