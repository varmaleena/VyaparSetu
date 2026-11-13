"""Synthesize the exact proposal read-back using the local Windows speech engine."""

import base64
import subprocess
import sys

from app.models.payment import PaymentProposal

_SPEAK = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$text = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String([Console]::In.ReadToEnd()))
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$audio = New-Object IO.MemoryStream
try {
    $speaker.SetOutputToWaveStream($audio)
    $speaker.Speak($text)
    $speaker.SetOutputToNull()
    [Console]::Write([Convert]::ToBase64String($audio.ToArray()))
} finally {
    $speaker.Dispose()
    $audio.Dispose()
}
"""


def payment_readback(proposal: PaymentProposal) -> str:
    def rupees(paise: int) -> str:
        whole, remainder = divmod(paise, 100)
        return f"{whole} rupees and {remainder} paise"

    last_four = " ".join(proposal.masked_account[-4:])
    text = (
        f"Simulated payment of {rupees(proposal.amount_paise)} to "
        f"{proposal.supplier_name}, account ending in {last_four}. "
        f"Pay by {proposal.deadline:%d %B %Y}."
    )
    option = proposal.option
    if option.principal:
        text += (
            f" Financing principal is {rupees(option.principal)}."
            f" Total repayment is {rupees(option.repayment_total)} over "
            f"{proposal.tenor_days} days, up to "
            f"{rupees(option.daily_installment)} per day."
        )
    return text


def synthesize_readback(text: str) -> bytes:
    if sys.platform != "win32":
        raise OSError("Windows speech synthesis is unavailable.")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SPEAK],
        input=base64.b64encode(text.encode("utf-8")),
        capture_output=True,
        timeout=15,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    audio = base64.b64decode(result.stdout, validate=True)
    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        raise ValueError("Speech synthesis did not return WAV audio.")
    return audio
