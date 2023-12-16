from typing import Dict, Union

from driftpy.math.orders import is_resting_limit_order, is_triggered, must_be_triggered
from driftpy.types import MarketType, Order, PerpMarketAccount, SpotMarketAccount, StateAccount, is_one_of_variant, is_variant, market_type_to_string

def add_order_list(market_type: str, market_index: int, order_lists):
    from driftpy.dlob.node_list import NodeList, MarketNodeLists
    order_lists: Dict[str, Dict[int, MarketNodeLists]]

    order_lists[market_type][market_index] = {
        'restingLimit': {
            'ask': NodeList('restingLimit', 'asc'),
            'bid': NodeList('restingLimit', 'desc'),
        },
        'floatingLimit': {
            'ask': NodeList('floatingLimit', 'asc'),
            'bid': NodeList('floatingLimit', 'desc'),
        },
        'takingLimit': {
            'ask': NodeList('takingLimit', 'asc'),
            'bid': NodeList('takingLimit', 'asc'),  # always sort ascending for market orders
        },
        'market': {
            'ask': NodeList('market', 'asc'),
            'bid': NodeList('market', 'asc'),  # always sort ascending for market orders
        },
        'trigger': {
            'above': NodeList('trigger', 'asc'),
            'below': NodeList('trigger', 'desc'),
        },
    }

    return order_lists


def get_list_identifiers(order: Order, slot: int, order_lists):
    from driftpy.dlob.DLOB_node import NodeType, MarketNodeLists
    order_lists: Dict[str, Dict[int, MarketNodeLists]]

    is_inactive_trigger_order = must_be_triggered(order) and not is_triggered(order)

    type: NodeType
    if is_inactive_trigger_order:
        type = 'trigger'
    elif is_one_of_variant(order.orderType, ['Market', 'TriggerMarket', 'Oracle']):
        type = 'market'
    elif order.oracle_price_offset != 0:
        type = 'floatingLimit'
    else:
        is_resting = is_resting_limit_order(order, slot)
        type = 'restingLimit' if is_resting else 'takingLimit'

    subtype: str
    if is_inactive_trigger_order:
        subtype = 'above' if is_variant(order.trigger_condition, 'Above') else 'below'
    else:
        subtype = 'bid' if is_variant(order.direction, 'Long') else 'ask'

    market_type = market_type_to_string(order.market_type)

    if not market_type in order_lists:
        return None
    
    return type, subtype

def get_maker_rebate(market_type: MarketType, state_account: StateAccount, market_account: Union[PerpMarketAccount, SpotMarketAccount]):
    if is_variant(market_type, 'Perp'):
        maker_rebate_numerator = \
            state_account.perp_fee_structure.fee_tiers[0].maker_rebate_numerator
        maker_rebate_denominator = \
            state_account.perp_fee_structure.fee_tiers[0].maker_rebate_denominator
    else:
        maker_rebate_numerator = \
            state_account.spot_fee_structure.fee_tiers[0].maker_rebate_numerator
        maker_rebate_denominator = \
            state_account.spot_fee_structure.fee_tiers[0].maker_rebate_denominator

    fee_adjustment = market_account.fee_adjustment if market_account.fee_adjustment is not None else 0
    if fee_adjustment != 0:
        maker_rebate_numerator += (maker_rebate_numerator * fee_adjustment) // 100

    return maker_rebate_numerator, maker_rebate_denominator