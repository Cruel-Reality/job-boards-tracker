from app.orm_models import JobApplication, JobPosting, JobStatusEnum


def test_application_status_none_when_not_tracked():
    job = JobPosting()
    assert job.application_status is None


def test_application_status_reflects_linked_application():
    job = JobPosting()
    job.application = JobApplication(status=JobStatusEnum.applied)
    assert job.application_status is JobStatusEnum.applied
