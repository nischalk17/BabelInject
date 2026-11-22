from aie.models.base import GenConfig, Message, ModelResponse, ToolCall


def test_message_with_tool_call_round_trips_json() -> None:
    msg = Message(
        role="assistant",
        content="नमस्ते",
        tool_calls=[ToolCall(id="call_0_0", name="read_email", arguments={"email_id": "e1"})],
    )
    assert Message.model_validate_json(msg.model_dump_json()) == msg


def test_response_round_trips_json() -> None:
    resp = ModelResponse(
        message=Message(role="assistant", content="hi"), model_tag="t", raw={"a": 1}
    )
    assert ModelResponse.model_validate_json(resp.model_dump_json()) == resp


def test_gen_config_defaults_to_temperature_zero() -> None:
    assert GenConfig().temperature == 0.0
