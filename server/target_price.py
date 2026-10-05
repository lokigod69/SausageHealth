"""The most the shop can pay for a unit and still keep its margin.

Calculation only: no network, no stored state, no clock.

The margin is taken *off the sell price*, not added onto the cost. Those are
different numbers -- at a 295 sell price and a 30% margin the ceiling is 206.50
one way and 226.92 the other -- and the catalogue settles which one the shop
actually buys by: recorded cost sits at 70.0% of the sell price at the third
quartile, forty variants sit exactly on it, and a single variant sits on the
other reading.

The figure exists to be read by a person in the shop before they order. It is
deliberately absent from the message that goes out to a supplier: it is our
margin, and a supplier who reads it knows the ceiling of every negotiation
after it.
"""
import os
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from urllib.parse import urlparse

DEFAULT_MARGIN = Decimal('0.30')
SHOPEE_HOSTS = ('shopee.ph', 'shp.ee')


def digits(value):
    """Exact plain notation, as `performance` does it.

    Defined here rather than imported from the POS reader on purpose: this
    module is arithmetic over figures it is handed, and it stays importable
    without pulling the reader in behind it.
    """
    return None if value is None else format(value, 'f')


def margin():
    """The share of the sell price the shop keeps.

    A bare `30` is refused rather than read as 30%: guessing between 30 and 0.30
    is a factor of a hundred on every ceiling in the shop.
    """
    raw = (os.environ.get('SH_TARGET_MARGIN') or '').strip()
    if not raw:
        return DEFAULT_MARGIN
    try:
        share = Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValueError('SH_TARGET_MARGIN must be a decimal share of the sell price, such as 0.30.')
    if not share.is_finite() or not Decimal(0) < share < Decimal(1):
        raise ValueError('SH_TARGET_MARGIN must be a decimal share above 0 and below 1, such as 0.30.')
    return share


def money(value):
    """A recorded amount, or None when there is no usable figure.

    Absent, unreadable and negative all become None: a ceiling computed from a
    number nobody can defend is worse than no ceiling on the screen.
    """
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def sell_price(variant, store_row):
    """What this store charges, or None when there is no price to work from.

    A variable-priced variant has no sell price at all -- the cashier types one
    in per sale -- so there is nothing to take a margin on.
    """
    store_row = store_row or {}
    pricing = store_row.get('pricing_type') or variant.get('default_pricing_type')
    if pricing and str(pricing).upper() != 'FIXED':
        return None
    if store_row.get('settings_present'):
        own = money(store_row.get('price'))
        if own is not None:
            return own
    return money(variant.get('default_price'))


def target(sell, share=None):
    """The highest unit price that still leaves the margin, rounded down.

    Down, to the centavo: rounding a ceiling upwards hands back headroom the
    margin does not actually have.
    """
    share = margin() if share is None else share
    return (sell * (Decimal(1) - share)).quantize(Decimal('0.01'), rounding=ROUND_FLOOR)


def implied_price(paid, share=None):
    """The sell price that restores the margin at a price actually paid.

    Up, to the whole peso: a till price is a round number, and rounding it down
    would reopen the very gap this figure exists to close.
    """
    share = margin() if share is None else share
    return (paid / (Decimal(1) - share)).quantize(Decimal('1'), rounding=ROUND_CEILING)


def shopee(url):
    """Whether a buy link really points at Shopee.

    Decided from the link's host rather than the supplier's name: a name can be
    edited, and a second Shopee seller would otherwise quietly miss out. Matched
    on the host itself or a subdomain of it, so a lookalike such as
    `shopee.ph.example.com` does not pass.
    """
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or '').lower()
    except ValueError:
        return False
    return any(host == known or host.endswith('.' + known) for known in SHOPEE_HOSTS)


def for_buy_link(variant, store_row, buy_url, share=None):
    """The ceiling, but only where the shop picks a price off a listing.

    Shopee only for now. There the person ordering reads a price on a page and
    decides whether to pay it, so a ceiling changes what they do. A butcher's or
    a distributor's price is quoted to us instead, and a ceiling printed next to
    a quote would only be noise on the screen.
    """
    if not shopee(buy_url):
        return {'target_buy_price': None, 'target_state': 'not_shopee', 'target_margin': None,
                'sell_price': None, 'recorded_cost': None, 'implied_price': None}
    return row(variant, store_row, share)


def row(variant, store_row, share=None):
    """What a person needs on screen before they buy this variant.

    `target_state` says how far to trust the ceiling:
      no_price -- nothing to compute from, so no ceiling is shown
      no_cost  -- a ceiling, but nothing recorded to compare it against
      ok       -- what the shop pays today already fits under it
      over     -- it does not, and `implied_price` is the till price that fixes it
    """
    share = margin() if share is None else share
    sell = sell_price(variant, store_row)
    result = {'target_buy_price': None, 'target_state': 'no_price', 'target_margin': digits(share),
              'sell_price': None, 'recorded_cost': None, 'implied_price': None}
    if sell is None:
        return result
    ceiling = target(sell, share)
    cost = money(variant.get('cost'))
    # Loyverse writes 0.00 into every cost nobody has filled in. Comparing a
    # ceiling against that would report the shop buys the item for nothing.
    if cost == 0:
        cost = None
    result.update(target_buy_price=digits(ceiling), sell_price=digits(sell),
                  recorded_cost=digits(cost), target_state='no_cost' if cost is None else 'ok')
    if cost is not None and cost > ceiling:
        result.update(target_state='over', implied_price=digits(implied_price(cost, share)))
    return result
