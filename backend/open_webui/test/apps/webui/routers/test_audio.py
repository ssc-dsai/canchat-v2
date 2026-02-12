import io
import json
from unittest.mock import patch, MagicMock, AsyncMock

from open_webui.test.util.abstract_integration_test import AbstractPostgresTest
from open_webui.test.util.mock_user import mock_webui_user
from open_webui.utils.auth import get_current_user


class TestAudio(AbstractPostgresTest):
    BASE_PATH = "/api/v1/audio"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.users import Users

        cls.users = Users

    def setup_method(self):
        super().setup_method()
        import open_webui.main

        self.app = open_webui.main.app

        # Set default audio config state
        self.app.state.config.TTS_OPENAI_API_BASE_URL = "http://localhost:11434/v1"
        self.app.state.config.TTS_OPENAI_API_KEY = "test-tts-key"
        self.app.state.config.TTS_API_KEY = "test-api-key"
        self.app.state.config.TTS_ENGINE = "openai"
        self.app.state.config.TTS_MODEL = "tts-1"
        self.app.state.config.TTS_VOICE = "alloy"
        self.app.state.config.TTS_SPLIT_ON = "punctuation"
        self.app.state.config.TTS_AZURE_SPEECH_REGION = "eastus"
        self.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT = "audio-16khz-128kbitrate-mono-mp3"
        self.app.state.config.STT_OPENAI_API_BASE_URL = "http://localhost:11434/v1"
        self.app.state.config.STT_OPENAI_API_KEY = "test-stt-key"
        self.app.state.config.STT_ENGINE = "openai"
        self.app.state.config.STT_MODEL = "whisper-1"
        self.app.state.config.WHISPER_MODEL = "base"

        # Insert user for mock
        self.users.insert_new_user(
            "1", "John Doe", "john.doe@openwebui.com", "/user.png", "user"
        )

    # ------------------------------------------------------------------ #
    # GET /config
    # ------------------------------------------------------------------ #
    def test_get_audio_config(self):
        with mock_webui_user(role="admin"):
            response = self.fast_api_client.get(self.create_url("/config"))
        assert response.status_code == 200
        data = response.json()

        assert "tts" in data
        assert "stt" in data

        tts = data["tts"]
        assert tts["OPENAI_API_BASE_URL"] == "http://localhost:11434/v1"
        assert tts["OPENAI_API_KEY"] == "test-tts-key"
        assert tts["API_KEY"] == "test-api-key"
        assert tts["ENGINE"] == "openai"
        assert tts["MODEL"] == "tts-1"
        assert tts["VOICE"] == "alloy"
        assert tts["SPLIT_ON"] == "punctuation"
        assert tts["AZURE_SPEECH_REGION"] == "eastus"
        assert tts["AZURE_SPEECH_OUTPUT_FORMAT"] == "audio-16khz-128kbitrate-mono-mp3"

        stt = data["stt"]
        assert stt["OPENAI_API_BASE_URL"] == "http://localhost:11434/v1"
        assert stt["OPENAI_API_KEY"] == "test-stt-key"
        assert stt["ENGINE"] == "openai"
        assert stt["MODEL"] == "whisper-1"
        assert stt["WHISPER_MODEL"] == "base"

    def test_get_audio_config_non_admin_forbidden(self):
        """Only admins should be able to access /config."""
        with mock_webui_user(role="user"):
            response = self.fast_api_client.get(self.create_url("/config"))
        assert response.status_code == 401

    # ------------------------------------------------------------------ #
    # POST /config/update
    # ------------------------------------------------------------------ #
    def test_update_audio_config(self):
        payload = {
            "tts": {
                "OPENAI_API_BASE_URL": "http://new-tts-url/v1",
                "OPENAI_API_KEY": "new-tts-key",
                "API_KEY": "new-api-key",
                "ENGINE": "elevenlabs",
                "MODEL": "eleven_multilingual_v2",
                "VOICE": "EXAVITQu4vr4xnSDxMaL",
                "SPLIT_ON": "sentence",
                "AZURE_SPEECH_REGION": "westus",
                "AZURE_SPEECH_OUTPUT_FORMAT": "audio-24khz-160kbitrate-mono-mp3",
            },
            "stt": {
                "OPENAI_API_BASE_URL": "http://new-stt-url/v1",
                "OPENAI_API_KEY": "new-stt-key",
                "ENGINE": "openai",
                "MODEL": "whisper-1",
                "WHISPER_MODEL": "large",
            },
        }

        with mock_webui_user(role="admin"):
            response = self.fast_api_client.post(
                self.create_url("/config/update"), json=payload
            )
        assert response.status_code == 200
        data = response.json()

        # Verify response reflects new values
        assert data["tts"]["OPENAI_API_BASE_URL"] == "http://new-tts-url/v1"
        assert data["tts"]["OPENAI_API_KEY"] == "new-tts-key"
        assert data["tts"]["API_KEY"] == "new-api-key"
        assert data["tts"]["ENGINE"] == "elevenlabs"
        assert data["tts"]["MODEL"] == "eleven_multilingual_v2"
        assert data["tts"]["VOICE"] == "EXAVITQu4vr4xnSDxMaL"
        assert data["tts"]["SPLIT_ON"] == "sentence"
        assert data["tts"]["AZURE_SPEECH_REGION"] == "westus"
        assert data["tts"]["AZURE_SPEECH_OUTPUT_FORMAT"] == "audio-24khz-160kbitrate-mono-mp3"
        assert data["stt"]["OPENAI_API_BASE_URL"] == "http://new-stt-url/v1"
        assert data["stt"]["OPENAI_API_KEY"] == "new-stt-key"
        assert data["stt"]["ENGINE"] == "openai"
        assert data["stt"]["MODEL"] == "whisper-1"
        assert data["stt"]["WHISPER_MODEL"] == "large"

        # Verify app state was actually updated
        assert self.app.state.config.TTS_ENGINE == "elevenlabs"
        assert self.app.state.config.TTS_MODEL == "eleven_multilingual_v2"
        assert self.app.state.config.STT_ENGINE == "openai"
        assert self.app.state.config.WHISPER_MODEL == "large"

    def test_update_audio_config_non_admin_forbidden(self):
        payload = {
            "tts": {
                "OPENAI_API_BASE_URL": "http://x",
                "OPENAI_API_KEY": "x",
                "API_KEY": "x",
                "ENGINE": "openai",
                "MODEL": "tts-1",
                "VOICE": "alloy",
                "SPLIT_ON": "punctuation",
                "AZURE_SPEECH_REGION": "",
                "AZURE_SPEECH_OUTPUT_FORMAT": "",
            },
            "stt": {
                "OPENAI_API_BASE_URL": "http://x",
                "OPENAI_API_KEY": "x",
                "ENGINE": "openai",
                "MODEL": "whisper-1",
                "WHISPER_MODEL": "base",
            },
        }
        with mock_webui_user(role="user"):
            response = self.fast_api_client.post(
                self.create_url("/config/update"), json=payload
            )
        assert response.status_code == 401

    def test_update_audio_config_missing_fields_returns_422(self):
        """Sending an incomplete payload should result in a validation error."""
        payload = {"tts": {"ENGINE": "openai"}}
        with mock_webui_user(role="admin"):
            response = self.fast_api_client.post(
                self.create_url("/config/update"), json=payload
            )
        assert response.status_code == 422

    # ------------------------------------------------------------------ #
    # POST /transcriptions
    # ------------------------------------------------------------------ #
    def test_transcription_unsupported_content_type(self):
        """Uploading a file with an unsupported content type should return 400."""
        file = io.BytesIO(b"not audio data")
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/transcriptions"),
                files={"file": ("test.txt", file, "text/plain")},
            )
        assert response.status_code == 400

    @patch("open_webui.routers.audio.transcribe")
    @patch("open_webui.routers.audio.compress_audio")
    def test_transcription_valid_audio(self, mock_compress, mock_transcribe):
        """Uploading a valid audio file should call transcribe and return the result."""
        mock_compress.side_effect = lambda fp: fp
        mock_transcribe.return_value = {"text": "hello world"}

        audio_bytes = b"\x00" * 1024  # dummy audio bytes
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/transcriptions"),
                files={"file": ("test.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "hello world"
        assert "filename" in data

    @patch("open_webui.routers.audio.transcribe")
    @patch("open_webui.routers.audio.compress_audio")
    def test_transcription_wav_format(self, mock_compress, mock_transcribe):
        mock_compress.side_effect = lambda fp: fp
        mock_transcribe.return_value = {"text": "wav transcription"}

        audio_bytes = b"\x00" * 512
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/transcriptions"),
                files={"file": ("test.wav", io.BytesIO(audio_bytes), "audio/wav")},
            )
        assert response.status_code == 200
        assert response.json()["text"] == "wav transcription"

    @patch("open_webui.routers.audio.transcribe")
    @patch("open_webui.routers.audio.compress_audio")
    def test_transcription_ogg_format(self, mock_compress, mock_transcribe):
        mock_compress.side_effect = lambda fp: fp
        mock_transcribe.return_value = {"text": "ogg transcription"}

        audio_bytes = b"\x00" * 512
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/transcriptions"),
                files={"file": ("test.ogg", io.BytesIO(audio_bytes), "audio/ogg")},
            )
        assert response.status_code == 200
        assert response.json()["text"] == "ogg transcription"

    @patch("open_webui.routers.audio.transcribe")
    @patch("open_webui.routers.audio.compress_audio")
    def test_transcription_m4a_format(self, mock_compress, mock_transcribe):
        mock_compress.side_effect = lambda fp: fp
        mock_transcribe.return_value = {"text": "m4a transcription"}

        audio_bytes = b"\x00" * 512
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/transcriptions"),
                files={"file": ("test.m4a", io.BytesIO(audio_bytes), "audio/x-m4a")},
            )
        assert response.status_code == 200
        assert response.json()["text"] == "m4a transcription"

    @patch("open_webui.routers.audio.transcribe")
    @patch("open_webui.routers.audio.compress_audio")
    def test_transcription_compress_error_returns_400(
        self, mock_compress, mock_transcribe
    ):
        """If compression fails, the endpoint should return 400."""
        mock_compress.side_effect = Exception("compression error")

        audio_bytes = b"\x00" * 512
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/transcriptions"),
                files={"file": ("test.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
            )
        assert response.status_code == 400

    @patch("open_webui.routers.audio.transcribe")
    @patch("open_webui.routers.audio.compress_audio")
    def test_transcription_transcribe_error_returns_400(
        self, mock_compress, mock_transcribe
    ):
        """If transcription fails, the endpoint should return 400."""
        mock_compress.side_effect = lambda fp: fp
        mock_transcribe.side_effect = Exception("transcription failed")

        audio_bytes = b"\x00" * 512
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/transcriptions"),
                files={"file": ("test.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
            )
        assert response.status_code == 400

    # ------------------------------------------------------------------ #
    # GET /models
    # ------------------------------------------------------------------ #
    def test_get_models_openai_engine(self):
        self.app.state.config.TTS_ENGINE = "openai"
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/models"))
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        model_ids = [m["id"] for m in data["models"]]
        assert "tts-1" in model_ids
        assert "tts-1-hd" in model_ids

    def test_get_models_unknown_engine_returns_empty(self):
        self.app.state.config.TTS_ENGINE = "unknown"
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/models"))
        assert response.status_code == 200
        assert response.json()["models"] == []

    @patch("open_webui.routers.audio.requests.get")
    def test_get_models_elevenlabs_engine(self, mock_get):
        self.app.state.config.TTS_ENGINE = "elevenlabs"
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"name": "Model A", "model_id": "model-a"},
            {"name": "Model B", "model_id": "model-b"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/models"))
        assert response.status_code == 200
        models = response.json()["models"]
        assert len(models) == 2
        assert models[0]["id"] == "model-a"
        assert models[1]["name"] == "Model B"

    # ------------------------------------------------------------------ #
    # GET /voices
    # ------------------------------------------------------------------ #
    def test_get_voices_openai_engine(self):
        self.app.state.config.TTS_ENGINE = "openai"
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/voices"))
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        voice_ids = [v["id"] for v in data["voices"]]
        expected = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        for v in expected:
            assert v in voice_ids

    def test_get_voices_unknown_engine_returns_empty(self):
        self.app.state.config.TTS_ENGINE = "unknown"
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/voices"))
        assert response.status_code == 200
        assert response.json()["voices"] == []

    @patch("open_webui.routers.audio.get_elevenlabs_voices")
    def test_get_voices_elevenlabs_engine(self, mock_elevenlabs):
        self.app.state.config.TTS_ENGINE = "elevenlabs"
        mock_elevenlabs.return_value = {
            "voice-1": "Voice One",
            "voice-2": "Voice Two",
        }

        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/voices"))
        assert response.status_code == 200
        voices = response.json()["voices"]
        assert len(voices) == 2
        voice_ids = [v["id"] for v in voices]
        assert "voice-1" in voice_ids
        assert "voice-2" in voice_ids

    @patch("open_webui.routers.audio.requests.get")
    def test_get_voices_azure_engine(self, mock_get):
        self.app.state.config.TTS_ENGINE = "azure"
        self.app.state.config.TTS_AZURE_SPEECH_REGION = "eastus"
        self.app.state.config.TTS_API_KEY = "azure-key"

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"ShortName": "en-US-Guy24kRUS", "DisplayName": "Guy"},
            {"ShortName": "en-US-Aria24kRUS", "DisplayName": "Aria"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/voices"))
        assert response.status_code == 200
        voices = response.json()["voices"]
        assert len(voices) == 2
        voice_ids = [v["id"] for v in voices]
        assert "en-US-Guy24kRUS" in voice_ids
        assert "en-US-Aria24kRUS" in voice_ids

    # ------------------------------------------------------------------ #
    # POST /speech
    # ------------------------------------------------------------------ #
    @patch("aiohttp.ClientSession")
    def test_speech_openai_engine(self, mock_session_cls):
        """Test TTS with the openai engine — mock the external HTTP call."""
        self.app.state.config.TTS_ENGINE = "openai"

        fake_audio = b"\xff\xfb\x90\x00" * 100  # fake mp3 bytes

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=fake_audio)
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        payload = {"input": "Hello world", "voice": "alloy"}
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/speech"),
                content=json.dumps(payload),
            )
        assert response.status_code == 200

    def test_speech_invalid_json_returns_400(self):
        """Sending non-JSON body should return 400."""
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/speech"),
                content=b"this is not json",
            )
        assert response.status_code == 400

    # ------------------------------------------------------------------ #
    # Utility function tests
    # ------------------------------------------------------------------ #
    def test_is_mp4_audio_nonexistent_file(self):
        from open_webui.routers.audio import is_mp4_audio

        result = is_mp4_audio("/nonexistent/path/file.mp4")
        assert result is False

    @patch("open_webui.routers.audio.mediainfo")
    def test_is_mp4_audio_true(self, mock_mediainfo):
        """File that has AAC codec in MP4 container should return True."""
        mock_mediainfo.return_value = {
            "codec_name": "aac",
            "codec_type": "audio",
            "codec_tag_string": "mp4a",
        }
        with patch("os.path.isfile", return_value=True):
            from open_webui.routers.audio import is_mp4_audio

            assert is_mp4_audio("/some/file.mp4") is True

    @patch("open_webui.routers.audio.mediainfo")
    def test_is_mp4_audio_false_wrong_codec(self, mock_mediainfo):
        mock_mediainfo.return_value = {
            "codec_name": "mp3",
            "codec_type": "audio",
            "codec_tag_string": "mp3a",
        }
        with patch("os.path.isfile", return_value=True):
            from open_webui.routers.audio import is_mp4_audio

            assert is_mp4_audio("/some/file.mp3") is False

    def test_compress_audio_small_file_passthrough(self):
        """Files below MAX_FILE_SIZE should be returned as-is."""
        import tempfile, os
        from open_webui.routers.audio import compress_audio, MAX_FILE_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(b"\x00" * 100)
            tmp_path = tmp.name

        try:
            result = compress_audio(tmp_path)
            assert result == tmp_path
        finally:
            os.unlink(tmp_path)
