"""Public release ratings, reviews, reactions and reporting."""

import uuid
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    PublishedRelease, ReleaseRating, ReleaseReview, ReleaseReviewReaction,
    ReleaseReviewReport, User,
)
from .projects import CurrentUser, DbSession
from .schemas import ReleaseRatingUpsert, ReleaseReviewReportCreate, ReleaseReviewUpsert

router = APIRouter(prefix="/api/public/releases", tags=["release feedback"])


def _release_or_404(db: Session, slug: str) -> PublishedRelease:
    release = db.scalar(select(PublishedRelease).where(PublishedRelease.slug == slug))
    if release is None or release.visibility == "private":
        raise HTTPException(status_code=404, detail="Release not found.")
    return release


def _review_or_404(db: Session, release_id: uuid.UUID, review_id: uuid.UUID) -> ReleaseReview:
    review = db.scalar(select(ReleaseReview).where(
        ReleaseReview.id == review_id, ReleaseReview.release_id == release_id,
    ))
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return review


@router.get("/{slug}/feedback")
def get_release_feedback(slug: str, db: DbSession):
    release = _release_or_404(db, slug)
    scores = db.execute(
        select(ReleaseRating.score, func.count(ReleaseRating.id))
        .where(ReleaseRating.release_id == release.id)
        .group_by(ReleaseRating.score)
    ).all()
    distribution = {str(score): 0 for score in range(1, 11)}
    rating_count = 0
    weighted_total = 0
    for score, count in scores:
        distribution[str(score)] = count
        rating_count += count
        weighted_total += score * count

    rows = db.execute(
        select(ReleaseReview, User.display_name)
        .join(User, User.id == ReleaseReview.user_id)
        .where(ReleaseReview.release_id == release.id, ReleaseReview.status == "visible")
        .order_by(ReleaseReview.created_at.desc())
        .limit(100)
    ).all()
    reviews = []
    for review, display_name in rows:
        helpful_count = db.scalar(select(func.count(ReleaseReviewReaction.id)).where(
            ReleaseReviewReaction.review_id == review.id,
            ReleaseReviewReaction.reaction == "helpful",
        )) or 0
        reviews.append({
            "id": str(review.id), "body": review.body,
            "contains_spoilers": review.contains_spoilers,
            "author_name": display_name, "created_at": review.created_at,
            "helpful_count": helpful_count,
        })
    return {
        "rating_count": rating_count,
        "average_score": round(weighted_total / rating_count, 2) if rating_count else None,
        "rating_distribution": distribution,
        "reviews": reviews,
    }


@router.put("/{slug}/rating")
def upsert_release_rating(slug: str, payload: ReleaseRatingUpsert, db: DbSession, user: CurrentUser):
    release = _release_or_404(db, slug)
    rating = db.scalar(select(ReleaseRating).where(
        ReleaseRating.release_id == release.id, ReleaseRating.user_id == user.id,
    ).with_for_update())
    if rating is None:
        rating = ReleaseRating(release_id=release.id, user_id=user.id, score=payload.score)
        db.add(rating)
    else:
        rating.score = payload.score
    db.commit()
    db.refresh(rating)
    return {"score": rating.score, "updated_at": rating.updated_at}


@router.put("/{slug}/review")
def upsert_release_review(slug: str, payload: ReleaseReviewUpsert, db: DbSession, user: CurrentUser):
    release = _release_or_404(db, slug)
    review = db.scalar(select(ReleaseReview).where(
        ReleaseReview.release_id == release.id, ReleaseReview.user_id == user.id,
    ).with_for_update())
    if review is None:
        review = ReleaseReview(
            release_id=release.id, user_id=user.id, body=payload.body,
            contains_spoilers=payload.contains_spoilers,
        )
        db.add(review)
    else:
        review.body = payload.body
        review.contains_spoilers = payload.contains_spoilers
        review.updated_at = func.now()
    db.commit()
    db.refresh(review)
    return {"id": str(review.id), "body": review.body, "contains_spoilers": review.contains_spoilers,
            "status": review.status, "updated_at": review.updated_at}


@router.put("/{slug}/reviews/{review_id}/helpful")
def react_helpful(slug: str, review_id: uuid.UUID, db: DbSession, user: CurrentUser):
    release = _release_or_404(db, slug)
    review = _review_or_404(db, release.id, review_id)
    if review.status != "visible":
        raise HTTPException(status_code=404, detail="Review not found.")
    if review.user_id == user.id:
        raise HTTPException(status_code=409, detail="You cannot react to your own review.")
    existing = db.scalar(select(ReleaseReviewReaction).where(
        ReleaseReviewReaction.review_id == review.id,
        ReleaseReviewReaction.user_id == user.id,
    ))
    if existing is None:
        db.add(ReleaseReviewReaction(review_id=review.id, user_id=user.id, reaction="helpful"))
        db.commit()
    count = db.scalar(select(func.count(ReleaseReviewReaction.id)).where(
        ReleaseReviewReaction.review_id == review.id,
    )) or 0
    return {"helpful_count": count, "reacted": True}


@router.delete("/{slug}/reviews/{review_id}/helpful")
def remove_helpful(slug: str, review_id: uuid.UUID, db: DbSession, user: CurrentUser):
    release = _release_or_404(db, slug)
    review = _review_or_404(db, release.id, review_id)
    reaction = db.scalar(select(ReleaseReviewReaction).where(
        ReleaseReviewReaction.review_id == review.id,
        ReleaseReviewReaction.user_id == user.id,
    ))
    if reaction is not None:
        db.delete(reaction)
        db.commit()
    count = db.scalar(select(func.count(ReleaseReviewReaction.id)).where(
        ReleaseReviewReaction.review_id == review.id,
    )) or 0
    return {"helpful_count": count, "reacted": False}


@router.post("/{slug}/reviews/{review_id}/reports", status_code=status.HTTP_201_CREATED)
def report_release_review(slug: str, review_id: uuid.UUID, payload: ReleaseReviewReportCreate, db: DbSession, user: CurrentUser):
    release = _release_or_404(db, slug)
    review = _review_or_404(db, release.id, review_id)
    if review.user_id == user.id:
        raise HTTPException(status_code=409, detail="You cannot report your own review.")
    if review.status != "visible":
        raise HTTPException(status_code=404, detail="Review not found.")
    existing = db.scalar(select(ReleaseReviewReport).where(
        ReleaseReviewReport.review_id == review.id,
        ReleaseReviewReport.reporter_user_id == user.id,
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already reported this review.")
    db.add(ReleaseReviewReport(review_id=review.id, reporter_user_id=user.id, reason=payload.reason))
    db.flush()
    report_count = db.scalar(select(func.count(ReleaseReviewReport.id)).where(
        ReleaseReviewReport.review_id == review.id,
    )) or 0
    # A small, explicit threshold limits continued exposure while preserving the report trail.
    if report_count >= 3:
        review.status = "hidden"
    db.commit()
    return {"reported": True, "review_hidden": review.status == "hidden"}
