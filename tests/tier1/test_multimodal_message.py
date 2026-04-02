"""Tests for multimodal Message support (ADR-068)."""

from app.llm.models import Message, MessageRole


class TestMultimodalMessage:

    def test_string_content_unchanged(self):
        msg = Message.user("hello")
        assert msg.content == "hello"
        assert msg.to_dict() == {"role": "user", "content": "hello"}

    def test_multimodal_content_blocks(self):
        blocks = [
            {"type": "text", "text": "Look at this:"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "abc123"}},
        ]
        msg = Message.user_multimodal(blocks)
        assert msg.role == MessageRole.USER
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2

    def test_multimodal_to_dict_preserves_blocks(self):
        blocks = [
            {"type": "text", "text": "context"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "xyz"}},
        ]
        msg = Message.user_multimodal(blocks)
        d = msg.to_dict()
        assert d["role"] == "user"
        assert isinstance(d["content"], list)
        assert d["content"][0]["type"] == "text"
        assert d["content"][1]["type"] == "image"

    def test_system_message_still_string(self):
        msg = Message.system("You are a helpful assistant")
        assert isinstance(msg.content, str)

    def test_assistant_message_still_string(self):
        msg = Message.assistant("Sure, I can help")
        assert isinstance(msg.content, str)
