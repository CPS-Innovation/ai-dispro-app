import re
from difflib import SequenceMatcher

from loguru import logger

BIGGEST_ALLOWED_GAP = 100  # characters to allow in between matching blocks for subset validation
SIMILARITY_THRESHOLD = 0.90  # X% similarity required for subset validation


def is_valid_subset(text: str, subset: str) -> bool:
    """Check if the subsets are valid parts of the original text with allowed fuzzy matching.

    Args:
        text: The original text.
        subset: The subset string to validate.

    Returns:
        bool: True if the subset is found within the text allowing for 5% character differences.

    """
    # Remove non-alphanumeric characters for comparison
    non_alphanum_pattern = re.compile(r"[^a-zA-Z0-9]")
    text_clean = non_alphanum_pattern.sub("", text.lower())
    subset_clean = non_alphanum_pattern.sub("", subset.lower())

    # If the cleaned subset is empty, consider it invalid
    if not subset_clean:
        logger.info("Cleaned subset is empty")
        return False

    # Try to find the best matching segment in the text
    matcher = SequenceMatcher(
        isjunk=None,
        a=text_clean,
        b=subset_clean,
        autojunk=False,
    )
    match_blocks = matcher.get_matching_blocks()

    # Concatenate nearby matching blocks
    concatenated_blocks = []
    curr_idx = 0
    while curr_idx < len(match_blocks):
        curr_block = match_blocks[curr_idx]
        concat_block = {"start": curr_block.a, "end": curr_block.a + curr_block.size}
        curr_idx += 1
        for end_idx in range(curr_idx, len(match_blocks)):
            next_block = match_blocks[end_idx]
            if next_block.size and next_block.a <= concat_block["end"] + BIGGEST_ALLOWED_GAP:
                concat_block["end"] = next_block.a + next_block.size
                curr_idx = end_idx
        logger.debug("Concatenated [%d:%d]: %s", concat_block["start"], concat_block["end"], text_clean[concat_block["start"]:concat_block["end"]])
        concatenated_blocks.append(concat_block)

    # Find the longest contiguous match
    best_ratio = max(((block["end"] - block["start"]) / len(subset_clean) for block in concatenated_blocks), default=0)

    # Allow for configured similarity threshold difference
    is_valid = best_ratio >= SIMILARITY_THRESHOLD

    if not is_valid:
        logger.info("Subset similarity too low (%.2f%%) for: %s", best_ratio * 100, subset_clean)

    return is_valid
