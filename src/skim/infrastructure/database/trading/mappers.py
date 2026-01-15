"""Mappers for converting between domain and persistence models"""

from datetime import datetime

from skim.domain.models import (
    Candidate,
    ORHCandidateData,
    Position,
    Ticker,
)
from skim.infrastructure.database.trading.models import (
    CandidateTable,
    ORHCandidateTable,
    PositionTable,
)


def map_table_to_candidate(
    table: CandidateTable, orh_table: ORHCandidateTable | None = None
) -> Candidate:
    """Map database tables to domain Candidate

    Args:
        table: Candidate database table
        orh_table: Optional ORH candidate database table

    Returns:
        Domain Candidate object
    """
    orh_data = None
    if orh_table:
        orh_data = ORHCandidateData(
            gap_percent=orh_table.gap_percent,
            conid=orh_table.conid,
            headline=orh_table.headline,
            announcement_type=orh_table.announcement_type,
            announcement_timestamp=(
                datetime.fromisoformat(orh_table.announcement_timestamp)
                if orh_table.announcement_timestamp
                else None
            ),
            or_high=orh_table.or_high or 0.0,
            or_low=orh_table.or_low or 0.0,
            sample_date=orh_table.sample_date,
        )

    return Candidate(
        ticker=Ticker.from_persistence(table.ticker),
        scan_date=datetime.fromisoformat(table.scan_date),
        status=table.status,
        strategy_name=table.strategy_name,
        created_at=datetime.fromisoformat(table.created_at),
        orh_data=orh_data,
    )


def map_candidate_to_table(candidate: Candidate) -> CandidateTable:
    """Map domain Candidate to database table

    Args:
        candidate: Domain Candidate object

    Returns:
        Candidate database table
    """
    strategy_name = candidate.strategy_name
    if not strategy_name and hasattr(candidate.__class__, "STRATEGY_NAME"):
        strategy_name = candidate.__class__.STRATEGY_NAME

    return CandidateTable(
        ticker=candidate.ticker.to_persistence(),
        scan_date=candidate.scan_date.isoformat(),
        status=candidate.status,
        strategy_name=strategy_name,
        created_at=candidate.created_at.isoformat(),
    )


def map_orh_data_to_table(
    ticker: str | Ticker, orh_data: ORHCandidateData | None
) -> ORHCandidateTable:
    """Map domain ORHCandidateData to database table

    Args:
        ticker: Stock ticker symbol (string)
        orh_data: Domain ORHCandidateData object

    Returns:
        ORHCandidate database table
    """
    if orh_data is None:
        orh_data = ORHCandidateData()

    ticker_str = ticker.symbol if isinstance(ticker, Ticker) else ticker

    return ORHCandidateTable(
        ticker=ticker_str,
        gap_percent=orh_data.gap_percent,
        conid=orh_data.conid,
        headline=orh_data.headline,
        announcement_type=orh_data.announcement_type,
        announcement_timestamp=(
            orh_data.announcement_timestamp.isoformat()
            if orh_data.announcement_timestamp
            else None
        ),
        or_high=orh_data.or_high,
        or_low=orh_data.or_low,
        sample_date=orh_data.sample_date,
    )


def map_table_to_position(table: PositionTable) -> Position:
    """Map database table to domain Position

    Args:
        table: Position database table

    Returns:
        Domain Position object
    """
    from skim.domain.models import Price, Ticker

    return Position(
        id=table.id,
        ticker=Ticker.from_persistence(table.ticker),
        quantity=table.quantity,
        entry_price=Price.from_persistence(table.entry_price),
        stop_loss=Price.from_persistence(table.stop_loss),
        entry_date=datetime.fromisoformat(table.entry_date),
        status=table.status,
        exit_price=Price.from_persistence(table.exit_price)
        if table.exit_price
        else None,
        exit_date=datetime.fromisoformat(table.exit_date)
        if table.exit_date
        else None,
    )


def map_position_to_table(position: Position) -> PositionTable:
    """Map domain Position to database table

    Args:
        position: Domain Position object

    Returns:
        Position database table
    """
    return PositionTable(
        id=position.id,
        ticker=position.ticker.to_persistence(),
        quantity=position.quantity,
        entry_price=position.entry_price.to_persistence(),
        stop_loss=position.stop_loss.to_persistence(),
        entry_date=position.entry_date.isoformat(),
        status=position.status,
        exit_price=position.exit_price.to_persistence()
        if position.exit_price
        else None,
        exit_date=position.exit_date.isoformat()
        if position.exit_date
        else None,
    )
