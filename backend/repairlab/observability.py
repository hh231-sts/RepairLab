import json
import threading

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult


class LocalSpanExporter(SpanExporter):
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()

    def export(self, spans):
        with self.lock, self.path.open("a", encoding="utf-8") as stream:
            for span in spans:
                # Only explicit execution metadata, no prompts, credentials or user file contents.
                stream.write(
                    json.dumps(
                        {
                            "trace_id": f"{span.context.trace_id:032x}",
                            "span_id": f"{span.context.span_id:016x}",
                            "name": span.name,
                            "start_ns": span.start_time,
                            "end_ns": span.end_time,
                            "status": span.status.status_code.name,
                            "attributes": dict(span.attributes or {}),
                        }
                    )
                    + "\n"
                )
        return SpanExportResult.SUCCESS


def local_tracer(data_root):
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(LocalSpanExporter(data_root / "otel.jsonl")))
    return provider, provider.get_tracer("repairlab")
