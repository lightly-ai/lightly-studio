"""Resolution from an MCAP sample to the recording its frames live in."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.dataset import env
from lightly_studio.errors import NotFoundError
from lightly_studio.resolvers import mcap_resolver


def resolve_recording_path(*, session: Session, sample_id: UUID) -> str:
    """Return the path of the recording an MCAP sample points into.

    An MCAP sample stores only a seek key, a channel id and a log time, so the recording
    itself has to be resolved separately before any bytes can be read. This function is
    the only place that resolution happens.

    Args:
        session: Database session.
        sample_id: The MCAP sample to resolve.

    Returns:
        A path or URL that fsspec can open.

    Raises:
        NotFoundError: The sample is not an MCAP sample, or no recording is configured
            for it.
    """
    # TODO(Kondrat, 09/2026): Resolve sample -> group -> sequence and read the stored
    # recording path once LIG-10634 adds it. Until then one configured recording stands
    # in for every sample: enough to drive the workspace in development, not shippable.
    if mcap_resolver.get_by_id(session=session, sample_id=sample_id) is None:
        raise NotFoundError(f"MCAP sample not found: {sample_id}")

    recording_path = env.LIGHTLY_STUDIO_MCAP_RECORDING_PATH
    if not recording_path:
        raise NotFoundError(
            "No recording is configured for MCAP samples. Set "
            "LIGHTLY_STUDIO_MCAP_RECORDING_PATH to an .mcap path until recording paths "
            "are stored per recording."
        )
    return recording_path
