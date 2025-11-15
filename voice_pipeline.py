import os
import uuid
import wave
import json
import time
from typing import Tuple

import boto3

# ------------------------------
# AWS CONFIG
# ------------------------------
S3_BUCKET = "<YOUR_BUCKET_NAME>"
REGION = "<YOUR_AWS_REGION>"

# Region where your Bedrock agents live
# (your console link shows us-east-2, so keep that if your agents are there)
BEDROCK_REGION = "us-east-2"

transcribe = boto3.client("transcribe", region_name=AWS_REGION)
polly = boto3.client("polly", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)
bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=BEDROCK_REGION)


def get_wav_duration_seconds(file_path: str) -> float:
    """Return duration (seconds) of a WAV file."""
    with wave.open(file_path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def upload_to_s3(local_path: str, key_prefix: str = "uploads/") -> str:
    """Upload the local file to S3 and return the s3:// URI."""
    file_name = os.path.basename(local_path)
    s3_key = f"{key_prefix}{uuid.uuid4()}_{file_name}"
    s3.upload_file(local_path, S3_BUCKET, s3_key)
    return f"s3://{S3_BUCKET}/{s3_key}"


def transcribe_audio(local_wav_path: str) -> str:
    """
    Send the WAV file to Amazon Transcribe and return the text transcript.
    """
    try:
        duration = get_wav_duration_seconds(local_wav_path)
        if duration < 0.5:
            raise ValueError(
                f"Audio too short ({duration:.2f}s). Please record at least 1–2 seconds."
            )
    except Exception:
        # If duration check fails (e.g., file header weird), just skip the duration check
        duration = None


    media_uri = upload_to_s3(local_wav_path)
    job_name = f"voice-agent-{uuid.uuid4()}"

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": media_uri},
        MediaFormat="wav",
        LanguageCode="en-US",
        OutputBucketName=S3_BUCKET,
    )

    # Wait for the job to complete (simple polling)
    while True:
        job = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        status = job["TranscriptionJob"]["TranscriptionJobStatus"]
        if status in ["COMPLETED", "FAILED"]:
            break
        time.sleep(2)

    if status == "FAILED":
        raise RuntimeError(f"Transcription failed: {job}")

    # Transcribe writes a JSON file with the transcript to S3.
    # By default, the key is "<job_name>.json"
    output_key = f"{job_name}.json"
    obj = s3.get_object(Bucket=S3_BUCKET, Key=output_key)
    data = json.loads(obj["Body"].read().decode("utf-8"))
    text = data["results"]["transcripts"][0]["transcript"]
    return text.strip()


def call_master_agent(user_text: str, session_id: str) -> str:
    """
    Call your Bedrock MASTER agent and return its text reply.
    YOU must fill in your agentId + agentAliasId from the console.
    """
    if not user_text:
        return "I didn't catch that. Could you please repeat your answer?"

    # TODO: replace with your actual IDs from Bedrock console
    
    AGENT_ID = "<YOUR_AGENT_ID>"
    AGENT_ALIAS_ID = "<YOUR_AGENT_ALIAS_ID>"


    response = bedrock_agent.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,   # same per user to keep conversation context
        inputText=user_text,
        enableTrace=False,
        endSession=False,
    )

    completion_text = ""

    # completion is an event stream; usually one chunk, but we loop just in case.
    for event in response.get("completion", []):
        chunk = event.get("chunk")
        if not chunk:
            continue
        bytes_data = chunk.get("bytes")
        if not bytes_data:
            continue
        completion_text += bytes_data.decode("utf-8")

    return completion_text.strip() or "Sorry, I couldn't generate a reply this time."


def synthesize_speech(text: str, output_path: str) -> str:
    """
    Use Amazon Polly to turn text into speech (MP3) and save it.
    """
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId="Joanna",
        Engine="neural",  # neural sounds more natural
    )
    with open(output_path, "wb") as f:
        f.write(response["AudioStream"].read())
    return output_path


def handle_voice_interaction(
    local_wav_path: str, output_audio_path: str, session_id: str
) -> Tuple[str, str, str]:
    """
    One TURN of the conversation:
    1) voice -> text (Transcribe)
    2) text -> reply (Bedrock MASTER agent, multi-turn via session_id)
    3) reply -> voice (Polly)
    """
    user_text = transcribe_audio(local_wav_path)
    agent_reply = call_master_agent(user_text, session_id)
    synthesize_speech(agent_reply, output_audio_path)
    return user_text, agent_reply, output_audio_path