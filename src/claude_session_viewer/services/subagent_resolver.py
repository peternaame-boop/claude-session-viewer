"""Discover, parse, and link subagent JSONL files to parent session chunks."""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from claude_session_viewer.services.jsonl_parser import stream_session_file
from claude_session_viewer.types.chunks import Chunk, ChunkType
from claude_session_viewer.types.messages import MessageType, ParsedMessage, ToolExecution
from claude_session_viewer.types.processes import Process
from claude_session_viewer.types.sessions import SessionMetrics
from claude_session_viewer.utils.token_estimator import calculate_cost

logger = logging.getLogger(__name__)

MEMBER_COLORS = [
    "#4A9EFF", "#FF6B6B", "#51CF66", "#FFD43B",
    "#CC5DE8", "#FF922B", "#22B8CF", "#F06595",
]

# Track color assignment per member name across calls
_member_color_map: dict[str, str] = {}
_color_index: int = 0


def _assign_member_color(member_name: str) -> str:
    """Assign a stable color to a member name using round-robin."""
    global _color_index
    if not member_name:
        return ""
    if member_name in _member_color_map:
        return _member_color_map[member_name]
    color = MEMBER_COLORS[_color_index % len(MEMBER_COLORS)]
    _member_color_map[member_name] = color
    _color_index += 1
    return color


def discover_subagents(session_dir: str) -> list[str]:
    """Find all agent-*.jsonl files in session_dir/subagents/.

    Filters out files matching 'acompact*' pattern (compaction artifacts).
    Returns sorted list of file paths.
    """
    subagents_dir = Path(session_dir) / "subagents"
    if not subagents_dir.is_dir():
        return []

    paths = []
    for f in subagents_dir.iterdir():
        if not f.is_file():
            continue
        if not f.name.endswith(".jsonl"):
            continue
        # Must start with "agent-", filter out compaction artifacts
        if not f.name.startswith("agent-"):
            continue
        if f.name.startswith("acompact"):
            continue
        paths.append(str(f))

    return sorted(paths)


def _extract_text_from_content(content) -> str:
    """Extract plain text from message content (string or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        parts.append(result_content)
                    elif isinstance(result_content, list):
                        for item in result_content:
                            if isinstance(item, dict):
                                parts.append(item.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def _extract_teammate_info(content_text: str) -> dict:
    """Extract info from <teammate-message> tags in content.

    Looks for attributes: summary, team_name, member_name.
    Returns dict with extracted values (empty strings if not found).
    """
    info: dict[str, str] = {
        "summary": "",
        "team_name": "",
        "member_name": "",
    }

    # Match <teammate-message ...> tag with attributes
    tag_match = re.search(r"<teammate-message\b([^>]*)>", content_text)
    if not tag_match:
        return info

    attrs = tag_match.group(1)

    summary_match = re.search(r'summary="([^"]*)"', attrs)
    if summary_match:
        info["summary"] = summary_match.group(1)

    team_match = re.search(r'team_name="([^"]*)"', attrs)
    if team_match:
        info["team_name"] = team_match.group(1)

    member_match = re.search(r'member_name="([^"]*)"', attrs)
    if member_match:
        info["member_name"] = member_match.group(1)

    return info


def parse_subagent(file_path: str) -> Process:
    """Parse a single subagent JSONL file into a Process.

    Uses stream_session_file to parse messages. Extracts:
    - id from filename (agent-{id}.jsonl -> {id})
    - start_time, end_time, duration_ms from message timestamps
    - metrics (token counts, cost) from message usage data
    - description from first user message content
      (looks for <teammate-message summary="..."> tag)
    - team info from <teammate-message> tag attributes
    """
    path = Path(file_path)

    # Extract agent id from filename: agent-{id}.jsonl -> {id}
    stem = path.stem  # e.g., "agent-abc123"
    agent_id = stem.removeprefix("agent-")

    messages = list(stream_session_file(file_path))

    # Calculate time boundaries
    if messages:
        start_time = messages[0].timestamp
        end_time = messages[-1].timestamp
        duration_ms = max(0, int((end_time - start_time).total_seconds() * 1000))
    else:
        now = datetime.now()
        start_time = now
        end_time = now
        duration_ms = 0

    # Calculate metrics
    metrics = SessionMetrics()
    model = ""
    for msg in messages:
        metrics.message_count += 1
        if msg.usage:
            metrics.input_tokens += msg.usage.input_tokens
            metrics.output_tokens += msg.usage.output_tokens
            metrics.cache_read_tokens += msg.usage.cache_read_input_tokens
            metrics.cache_creation_tokens += msg.usage.cache_creation_input_tokens
            metrics.total_tokens += msg.usage.total
        if msg.model and not model:
            model = msg.model
        for _tc in msg.tool_calls:
            metrics.tool_call_count += 1

    if model:
        metrics.cost_usd = calculate_cost(
            metrics.input_tokens,
            metrics.output_tokens,
            metrics.cache_read_tokens,
            metrics.cache_creation_tokens,
            model,
        )
    metrics.duration_ms = duration_ms

    # Extract description and team info from first user message
    description = ""
    team_name = ""
    member_name = ""
    subagent_type = ""

    for msg in messages:
        if msg.type == MessageType.USER and not msg.is_meta:
            content_text = _extract_text_from_content(msg.content)
            teammate_info = _extract_teammate_info(content_text)

            if teammate_info["summary"]:
                description = teammate_info["summary"]
            elif content_text:
                # Fallback: use first 200 chars of content as description
                description = content_text[:200].strip()

            team_name = teammate_info["team_name"]
            member_name = teammate_info["member_name"]
            break

    # Determine member color
    member_color = _assign_member_color(member_name)

    return Process(
        id=agent_id,
        file_path=file_path,
        messages=messages,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        metrics=metrics,
        description=description,
        subagent_type=subagent_type,
        is_parallel=False,
        parent_task_id="",
        is_ongoing=False,
        team_name=team_name,
        member_name=member_name,
        member_color=member_color,
    )


def resolve_subagents(chunks: list[Chunk], session_dir: str) -> list[Chunk]:
    """Link subagent processes to their parent AI chunks.

    3-phase linking algorithm:

    Phase 1 - Result-based:
      Look at tool_results in AI chunk messages for results containing
      'agentId: {shortId}' (via toolUseResult data stored in parsed messages).
      Match the shortId to a discovered subagent file.

    Phase 2 - Description-based:
      For unlinked subagents, match Task tool call descriptions
      (task_description field) to the subagent's description. Uses fuzzy
      matching: checks if task description is contained in subagent summary
      or vice versa.

    Phase 3 - Positional fallback:
      Sort remaining unlinked subagents by start_time. Sort remaining
      unlinked Task tool executions by start_time. Match 1:1 in order.

    After linking, sets parent_task_id and detects parallel execution
    (subagents starting within 100ms of each other).
    """
    # Discover and parse all subagent files
    subagent_paths = discover_subagents(session_dir)
    if not subagent_paths:
        return chunks

    # Parse all subagents
    subagent_map: dict[str, Process] = {}
    for path in subagent_paths:
        process = parse_subagent(path)
        subagent_map[process.id] = process

    linked_agent_ids: set[str] = set()
    linked_tool_ids: set[str] = set()

    # Build index of AI chunks with their Task tool executions
    ai_chunks: list[Chunk] = [c for c in chunks if c.chunk_type == ChunkType.AI]

    # Phase 1 - Result-based linking
    # Look for agent IDs in tool result messages (via source_tool_use_id or
    # toolUseResult agentId pattern in raw message content)
    for chunk in ai_chunks:
        for msg in chunk.messages:
            for tr in msg.tool_results:
                # Check tool result content for agent ID references
                result_text = ""
                if isinstance(tr.content, str):
                    result_text = tr.content
                elif isinstance(tr.content, list):
                    for item in tr.content:
                        if isinstance(item, dict):
                            result_text += item.get("text", "")
                        elif isinstance(item, str):
                            result_text += item

                # Also check agent_id from the message itself
                # The toolUseResult.agentId appears as msg.agent_id in some cases
                # or we search for "agent-{id}" patterns in content

                for agent_id, process in subagent_map.items():
                    if agent_id in linked_agent_ids:
                        continue

                    # Check if this tool result references this agent
                    # Pattern: agentId in the toolUseResult, or agent-{id} in content
                    full_agent_ref = f"agent-{agent_id}"
                    short_ref = f"agentId: {agent_id}"
                    alt_ref = f'agentId":"{full_agent_ref}"'
                    alt_ref2 = f'"agentId":"{full_agent_ref}"'

                    if (full_agent_ref in result_text
                            or short_ref in result_text
                            or alt_ref in result_text
                            or alt_ref2 in result_text):
                        # Find the matching Task tool execution
                        matched_exec = _find_task_exec_for_tool_result(
                            chunk, tr.tool_use_id, linked_tool_ids,
                        )
                        if matched_exec:
                            process.parent_task_id = matched_exec.call.id
                            linked_agent_ids.add(agent_id)
                            linked_tool_ids.add(matched_exec.call.id)
                            chunk.processes.append(process)
                            break

        # Also check raw message data for toolUseResult agent references
        for msg in chunk.messages:
            if msg.agent_id and msg.agent_id.startswith("agent-"):
                ref_id = msg.agent_id.removeprefix("agent-")
                if ref_id in subagent_map and ref_id not in linked_agent_ids:
                    process = subagent_map[ref_id]
                    # Find a Task execution in this chunk for the tool result
                    for tr in msg.tool_results:
                        matched_exec = _find_task_exec_for_tool_result(
                            chunk, tr.tool_use_id, linked_tool_ids,
                        )
                        if matched_exec:
                            process.parent_task_id = matched_exec.call.id
                            linked_agent_ids.add(ref_id)
                            linked_tool_ids.add(matched_exec.call.id)
                            chunk.processes.append(process)
                            break

    # Phase 2 - Description-based linking
    for chunk in ai_chunks:
        for tex in chunk.tool_executions:
            if not tex.call.is_task:
                continue
            if tex.call.id in linked_tool_ids:
                continue

            task_desc = tex.call.task_description.strip().lower()
            if not task_desc:
                continue

            for agent_id, process in subagent_map.items():
                if agent_id in linked_agent_ids:
                    continue

                proc_desc = process.description.strip().lower()
                if not proc_desc:
                    continue

                # Fuzzy match: one contains the other
                if task_desc in proc_desc or proc_desc in task_desc:
                    process.parent_task_id = tex.call.id
                    linked_agent_ids.add(agent_id)
                    linked_tool_ids.add(tex.call.id)
                    chunk.processes.append(process)
                    break

    # Phase 3 - Positional fallback
    remaining_agents = [
        subagent_map[aid] for aid in sorted(
            subagent_map.keys(),
            key=lambda aid: subagent_map[aid].start_time,
        )
        if aid not in linked_agent_ids
    ]

    remaining_task_execs: list[tuple[Chunk, ToolExecution]] = []
    for chunk in ai_chunks:
        for tex in chunk.tool_executions:
            if tex.call.is_task and tex.call.id not in linked_tool_ids:
                remaining_task_execs.append((chunk, tex))

    remaining_task_execs.sort(
        key=lambda ct: ct[1].start_time or ct[0].start_time,
    )

    for i, process in enumerate(remaining_agents):
        if i >= len(remaining_task_execs):
            break
        chunk, tex = remaining_task_execs[i]
        process.parent_task_id = tex.call.id
        linked_agent_ids.add(process.id)
        linked_tool_ids.add(tex.call.id)
        chunk.processes.append(process)

    # Detect parallel execution
    _detect_parallel_execution(chunks)

    return chunks


def _find_task_exec_for_tool_result(
    chunk: Chunk,
    tool_use_id: str,
    linked_tool_ids: set[str],
) -> ToolExecution | None:
    """Find the Task tool execution that matches a given tool_use_id.

    First tries an exact match on tool_use_id. If that fails or the matched
    execution is not a Task, falls back to the first unlinked Task execution.
    """
    # Try exact match first
    for tex in chunk.tool_executions:
        if tex.call.id == tool_use_id and tex.call.is_task:
            if tex.call.id not in linked_tool_ids:
                return tex

    # Fallback: first unlinked Task execution in this chunk
    for tex in chunk.tool_executions:
        if tex.call.is_task and tex.call.id not in linked_tool_ids:
            return tex

    return None


def _detect_parallel_execution(chunks: list[Chunk]) -> None:
    """Mark subagents as parallel if they start within 100ms of each other."""
    for chunk in chunks:
        if len(chunk.processes) < 2:
            continue

        # Sort by start time
        sorted_procs = sorted(chunk.processes, key=lambda p: p.start_time)

        for i in range(len(sorted_procs)):
            for j in range(i + 1, len(sorted_procs)):
                delta = abs(
                    (sorted_procs[j].start_time - sorted_procs[i].start_time)
                    .total_seconds() * 1000
                )
                if delta <= 100:
                    sorted_procs[i].is_parallel = True
                    sorted_procs[j].is_parallel = True
