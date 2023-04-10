import argparse
from pyspark.sql import SparkSession
from pyspark.sql.types import StringType
from pyspark.sql.functions import udf, col
from google.cloud import bigquery
import nltk
nltk.download('vader_lexicon', download_dir='/home/nltk_data/')
from nltk.sentiment.vader import SentimentIntensityAnalyzer

def parse_args():
    parser = argparse.ArgumentParser() 
    parser.add_argument("--WATERMARK", required=True)
    return parser.parse_args()

def format_output(output_dict):
  
    polarity = "neutral"

    if(output_dict['compound']>= 0.05):
        polarity = "positive"

    elif(output_dict['compound']<= -0.05):
        polarity = "negative"

    return polarity

@udf(returnType=StringType())
def predict_sentiment(text):
    
    analyzer = SentimentIntensityAnalyzer()

    output_dict =  analyzer.polarity_scores(text)
    return format_output(output_dict)

def extract_from_bq(spark, timestamp):
    bq_client = bigquery.Client()
    query = f"""
            select tweet_id, tweet_text, tb.timestamp
            from `artful-fragment-380106.tweets.tweet_raw` tb
            where parse_datetime('%Y-%m-%d %H:%M:%E*S', tb.timestamp) > "{timestamp}";
            """
    output_table = bq_client.query(query)
    output_table.result()
    df = spark.read.format('bigquery') \
            .option('dataset', output_table.destination.dataset_id) \
            .load(output_table.destination.table_id)
    return df

def transform(df):
    df2 = df.withColumn('sentiment_prediction', predict_sentiment(col('tweet_text'))) \
            .select(col('tweet_id'), col('tweet_text'), col('sentiment_prediction'), col('timestamp'))
    return df2

def start_spark():
    spark_session = ( SparkSession.builder
                .config("spark.sql.repl.eagerEval.enabled", True)
                .master("yarn")
                .appName("spark-bigquery")
                .config('spark.jars', 'gs://spark-lib/bigquery/spark-bigquery-with-dependencies_2.11-0.29.0.jar')
                .config("spark.jars.packages", "com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.18.0")
                .getOrCreate() )
    return spark_session

args = parse_args()
WATERMARK = args.WATERMARK
spark = start_spark()
df = extract_from_bq(spark, timestamp=WATERMARK)
df2 = transform(df)
df2.write \
        .format("bigquery") \
        .option('table', 'tweets.tweets_analyzed') \
        .option("encoding", "UTF-8") \
        .mode("append") \
        .option("temporaryGcsBucket","dataproc-temp-us-central1-782182507587-lupgss8j") \
        .save()
spark.stop()
