import asyncio
import random
import config

async def human_delay(min_sec: float = None, max_sec: float = None):
    """Pause execution for a realistic human duration."""
    min_s = min_sec or config.MIN_ACTION_DELAY
    max_s = max_sec or config.MAX_ACTION_DELAY
    wait_time = random.uniform(min_s, max_s)
    await asyncio.sleep(wait_time)

async def human_move_and_click(page, locator):
    """
    Moves mouse smoothly to element with natural jitter, hovers, and clicks.
    """
    box = await locator.bounding_box()
    if not box:
        await locator.click()
        return

    # Add random offset within element boundaries (avoid clicking exact geometric center every time)
    offset_x = random.uniform(box["width"] * 0.25, box["width"] * 0.75)
    offset_y = random.uniform(box["height"] * 0.25, box["height"] * 0.75)
    target_x = box["x"] + offset_x
    target_y = box["y"] + offset_y

    # Simulate realistic mouse approach with intermediate points
    steps = random.randint(5, 12)
    await page.mouse.move(target_x, target_y, steps=steps)
    await human_delay(0.2, 0.5)
    await page.mouse.click(target_x, target_y)
    await human_delay(0.4, 0.9)

async def human_scroll(page, direction: str = "down", amount: int = None):
    """Scroll page naturally like a human reading content."""
    delta = amount or random.randint(250, 600)
    if direction == "up":
        delta = -delta

    # Split scroll into a few micro-scroll steps
    chunks = random.randint(3, 6)
    chunk_delta = delta / chunks
    for _ in range(chunks):
        await page.mouse.wheel(0, chunk_delta)
        await asyncio.sleep(random.uniform(0.05, 0.15))
    await human_delay(0.5, 1.2)

async def dismiss_wp_notices(page):
    """Dismiss common WordPress admin banners and modal popups."""
    try:
        dismiss_buttons = page.locator(
            "button.notice-dismiss, .is-dismissible .notice-dismiss, "
            "button[aria-label='Dismiss this notice'], a:has-text('Dismiss'), "
            "a:has-text('Remind me later'), button:has-text('Dismiss')"
        )
        count = await dismiss_buttons.count()
        for i in range(min(count, 5)):
            btn = dismiss_buttons.nth(i)
            if await btn.is_visible():
                await btn.click(timeout=1000)
                await asyncio.sleep(0.3)
    except Exception:
        pass

