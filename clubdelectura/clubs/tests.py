from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from books.models import Book, BookRating
from clubs.forms import ClubMeetingForm
from clubs.models import (
    Club,
    ClubLocation,
    ClubMeeting,
    ClubMembership,
    ReadingList,
    ReadingListItem,
)
from locations.models import Location


def make_user(email):
    return CustomUser.objects.create_user(
        email=email, password="password123", first_name="First", last_name="Last"
    )


def make_club_with_member(name="Book Lovers", email="member@example.com"):
    owner = make_user("owner@example.com")
    club = Club.objects.create(name=name, created_by=owner)
    member = make_user(email)
    ClubMembership.objects.create(user=member, club=club)
    ClubMembership.objects.create(user=owner, club=club)
    return club, member, owner


class ClubModelTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()

    def test_next_meeting_ignores_past_meetings(self):
        past_location = Location.objects.create(name="Old Cafe")
        ClubMeeting.objects.create(
            club=self.club,
            location=past_location,
            date=timezone.now() - timedelta(days=5),
        )
        future_meeting = ClubMeeting.objects.create(
            club=self.club,
            location=past_location,
            date=timezone.now() + timedelta(days=5),
        )

        self.assertEqual(self.club.next_meeting(), future_meeting)

    def test_next_meeting_returns_none_when_no_upcoming_meetings(self):
        Location.objects.create(name="Old Cafe")
        self.assertIsNone(self.club.next_meeting())

    def test_next_meeting_picks_the_soonest_of_several(self):
        location = Location.objects.create(name="Cafe")
        soonest = ClubMeeting.objects.create(
            club=self.club, location=location, date=timezone.now() + timedelta(days=1)
        )
        ClubMeeting.objects.create(
            club=self.club, location=location, date=timezone.now() + timedelta(days=10)
        )

        self.assertEqual(self.club.next_meeting(), soonest)

    def test_get_rated_books_only_counts_club_members(self):
        outsider = make_user("outsider@example.com")
        book = Book.objects.create(title="Dune", year=1965)

        BookRating.objects.create(book=book, user=self.member, rating=8)
        BookRating.objects.create(book=book, user=self.owner, rating=6)
        BookRating.objects.create(book=book, user=outsider, rating=10)

        rated = self.club.get_rated_books().get(pk=book.pk)

        self.assertEqual(rated.n_ratings, 2)
        self.assertEqual(rated.avg_rating, 7)


class ClubMembershipConstraintTests(TestCase):
    def test_club_location_cannot_be_duplicated(self):
        owner = make_user("owner@example.com")
        club = Club.objects.create(name="Club", created_by=owner)
        location = Location.objects.create(name="Library")
        ClubLocation.objects.create(club=club, location=location)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClubLocation.objects.create(club=club, location=location)


class ClubCRUDViewTests(TestCase):
    def setUp(self):
        self.user = make_user("creator@example.com")
        self.client.force_login(self.user)

    def test_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("clubs:club-list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_create_club_redirects_to_club_list(self):
        response = self.client.post(
            reverse("clubs:club-create"),
            {"name": "New Club", "description": "A club.", "members": [self.user.pk]},
        )

        self.assertRedirects(response, reverse("clubs:club-list"))
        self.assertTrue(Club.objects.filter(name="New Club").exists())

    def test_create_club_adds_creator_as_member(self):
        # Regression test: creating a club used to only set created_by,
        # without a ClubMembership - which would immediately lock the
        # creator out of managing their own club once membership is
        # required for update/delete. Deliberately not selecting the
        # creator in "members" here, to prove they get added regardless
        # of what was picked in the form.
        other_user = make_user("other@example.com")

        response = self.client.post(
            reverse("clubs:club-create"),
            {
                "name": "New Club",
                "description": "A club.",
                "members": [other_user.pk],
            },
        )

        self.assertEqual(response.status_code, 302)
        club = Club.objects.get(name="New Club")
        self.assertTrue(
            ClubMembership.objects.filter(user=self.user, club=club).exists()
        )

    def test_update_club_redirects_to_club_list(self):
        club = Club.objects.create(name="Old Name", created_by=self.user)
        ClubMembership.objects.create(user=self.user, club=club)

        response = self.client.post(
            reverse("clubs:club-update", kwargs={"pk": club.pk}),
            {"name": "Updated Name", "description": "", "members": [self.user.pk]},
        )

        self.assertRedirects(response, reverse("clubs:club-list"))
        club.refresh_from_db()
        self.assertEqual(club.name, "Updated Name")

    def test_update_club_forbidden_for_non_member(self):
        club, member, owner = make_club_with_member()

        response = self.client.get(reverse("clubs:club-update", kwargs={"pk": club.pk}))

        self.assertEqual(response.status_code, 403)

    def test_update_club_redirects_anonymous_to_login(self):
        club, member, owner = make_club_with_member()
        self.client.logout()

        response = self.client.get(reverse("clubs:club-update", kwargs={"pk": club.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_delete_club_redirects_to_club_list(self):
        club = Club.objects.create(name="Doomed Club", created_by=self.user)
        ClubMembership.objects.create(user=self.user, club=club)

        response = self.client.post(reverse("clubs:club-delete", kwargs={"pk": club.pk}))

        self.assertRedirects(response, reverse("clubs:club-list"))
        self.assertFalse(Club.objects.filter(pk=club.pk).exists())

    def test_delete_club_forbidden_for_non_member(self):
        club, member, owner = make_club_with_member()

        response = self.client.get(reverse("clubs:club-delete", kwargs={"pk": club.pk}))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Club.objects.filter(pk=club.pk).exists())


class ReadingListAccessTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")

    def test_club_reading_list_visible_to_member(self):
        reading_list = ReadingList.objects.create(
            name="Sci-fi", club=self.club, created_by=self.owner
        )
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("clubs:reading-list-detail-panel", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_club_reading_list_forbidden_to_non_member(self):
        reading_list = ReadingList.objects.create(
            name="Sci-fi", club=self.club, created_by=self.owner
        )
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse("clubs:reading-list-detail-panel", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_personal_reading_list_visible_to_creator_only(self):
        reading_list = ReadingList.objects.create(name="My List", created_by=self.owner)
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("clubs:reading-list-detail-panel", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_personal_reading_list_forbidden_to_others(self):
        reading_list = ReadingList.objects.create(name="My List", created_by=self.owner)
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("clubs:reading-list-detail-panel", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_full_detail_view_forbidden_to_non_member(self):
        # ReadingListDetailView (the full page, not the partial) never had
        # this check at all before - only its partial-view sibling did.
        reading_list = ReadingList.objects.create(
            name="Sci-fi", club=self.club, created_by=self.owner
        )
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse("clubs:reading-list-detail", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_full_detail_view_redirects_anonymous_to_login(self):
        reading_list = ReadingList.objects.create(
            name="Sci-fi", club=self.club, created_by=self.owner
        )

        response = self.client.get(
            reverse("clubs:reading-list-detail", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class ReadingListMutationPermissionTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")

    def test_member_can_open_update_form_for_club_list(self):
        reading_list = ReadingList.objects.create(
            name="Sci-fi", club=self.club, created_by=self.owner
        )
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("clubs:reading-list-update", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_non_member_forbidden_from_update_form_for_club_list(self):
        reading_list = ReadingList.objects.create(
            name="Sci-fi", club=self.club, created_by=self.owner
        )
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse("clubs:reading-list-update", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_creator_can_delete_personal_list(self):
        reading_list = ReadingList.objects.create(name="My List", created_by=self.owner)
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("clubs:reading-list-delete", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ReadingList.objects.filter(pk=reading_list.pk).exists())

    def test_non_creator_forbidden_from_deleting_personal_list(self):
        reading_list = ReadingList.objects.create(name="My List", created_by=self.owner)
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("clubs:reading-list-delete", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(ReadingList.objects.filter(pk=reading_list.pk).exists())

    def test_anonymous_redirected_to_login_from_update_form(self):
        reading_list = ReadingList.objects.create(
            name="Sci-fi", club=self.club, created_by=self.owner
        )

        response = self.client.get(
            reverse("clubs:reading-list-update", kwargs={"pk": reading_list.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class ReadingListCreateViewAnonymousTests(TestCase):
    def test_anonymous_user_is_redirected_not_crashed(self):
        # Regression test: ReadingListCreateView used to have no
        # LoginRequiredMixin at all, and unconditionally passed
        # request.user into ReadingListForm, which called user.clubs.all()
        # - AnonymousUser has no .clubs attribute, so this raised an
        # unhandled AttributeError (500) instead of redirecting to login.
        response = self.client.get(reverse("clubs:reading-list-create"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class ReadingListCreateFormTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.other_club = Club.objects.create(name="Other Club", created_by=self.owner)

    def test_club_field_is_preset_and_disabled_when_club_id_given(self):
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("clubs:reading-list-create") + f"?club_id={self.club.pk}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].fields["club"].disabled)
        self.assertEqual(response.context["form"].fields["club"].initial, self.club)

    def test_club_choices_limited_to_users_own_clubs(self):
        self.client.force_login(self.member)

        response = self.client.get(reverse("clubs:reading-list-create"))

        club_queryset = response.context["form"].fields["club"].queryset
        self.assertIn(self.club, club_queryset)
        self.assertNotIn(self.other_club, club_queryset)


class ClubMeetingAccessTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")
        self.location = Location.objects.create(name="Library")
        self.meeting = ClubMeeting.objects.create(
            club=self.club, location=self.location, date=timezone.now()
        )

    def test_member_can_view_meeting(self):
        self.client.force_login(self.member)
        response = self.client.get(
            reverse("clubs:club-meeting-detail", kwargs={"pk": self.meeting.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_outsider_cannot_view_meeting(self):
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse("clubs:club-meeting-detail", kwargs={"pk": self.meeting.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        # Regression test: this view used to run its own membership check
        # (via a hand-rolled dispatch()) before LoginRequiredMixin's check
        # ever got a chance to run, so anonymous users got a bare 403
        # instead of a login redirect. Fixed by moving onto
        # ClubMemberRequiredMixin, which checks authentication first.
        response = self.client.get(
            reverse("clubs:club-meeting-detail", kwargs={"pk": self.meeting.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class ClubMeetingMutationPermissionTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")
        self.location = Location.objects.create(name="Library")
        ClubLocation.objects.create(club=self.club, location=self.location)
        self.meeting = ClubMeeting.objects.create(
            club=self.club, location=self.location, date=timezone.now()
        )

    def test_member_can_open_create_form(self):
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("clubs:club-meeting-create", kwargs={"club_id": self.club.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_non_member_forbidden_from_create_form(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse("clubs:club-meeting-create", kwargs={"club_id": self.club.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirected_from_create_form(self):
        response = self.client.get(
            reverse("clubs:club-meeting-create", kwargs={"club_id": self.club.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_member_can_open_update_form(self):
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("clubs:club-meeting-update", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_non_member_forbidden_from_update_form(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse("clubs:club-meeting-update", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_non_member_forbidden_from_deleting_meeting(self):
        self.client.force_login(self.outsider)

        response = self.client.post(
            reverse("clubs:club-meeting-delete", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(ClubMeeting.objects.filter(pk=self.meeting.pk).exists())

    def test_member_can_delete_meeting(self):
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("clubs:club-meeting-delete", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClubMeeting.objects.filter(pk=self.meeting.pk).exists())


class ClubMeetingFormLocationTests(TestCase):
    def test_location_choices_limited_to_club_locations(self):
        club, member, owner = make_club_with_member()
        other_club = Club.objects.create(name="Other Club", created_by=owner)

        club_location = Location.objects.create(name="Library")
        ClubLocation.objects.create(club=club, location=club_location)

        unrelated_location = Location.objects.create(name="Unrelated Cafe")
        ClubLocation.objects.create(club=other_club, location=unrelated_location)

        form = ClubMeetingForm(club=club)

        self.assertIn(club_location, form.fields["location"].queryset)
        self.assertNotIn(unrelated_location, form.fields["location"].queryset)


class ClubBookRatingListViewTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")
        self.book = Book.objects.create(title="Dune", year=1965)
        BookRating.objects.create(book=self.book, user=self.member, rating=9)
        BookRating.objects.create(book=self.book, user=self.outsider, rating=1)

    def test_only_shows_ratings_from_club_members(self):
        self.client.force_login(self.member)

        response = self.client.get(
            reverse(
                "clubs:club-book-rating",
                kwargs={"club_id": self.club.pk, "book_id": self.book.pk},
            )
        )

        ratings = list(response.context["book_ratings"])
        self.assertEqual(len(ratings), 1)
        self.assertEqual(ratings[0].user, self.member)

    def test_forbidden_for_non_member(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse(
                "clubs:club-book-rating",
                kwargs={"club_id": self.club.pk, "book_id": self.book.pk},
            )
        )

        self.assertEqual(response.status_code, 403)


class ReadingListItemAPITests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.reading_list = ReadingList.objects.create(
            name="Sci-fi", club=self.club, created_by=self.owner
        )
        self.book = Book.objects.create(title="Dune", year=1965)
        self.client.force_login(self.member)

    def test_create_reading_list_item_sets_added_by(self):
        response = self.client.post(
            reverse("clubs:api-reading-list-item-list"),
            {"reading_list": self.reading_list.pk, "book": self.book.pk},
        )

        self.assertEqual(response.status_code, 201)
        item = ReadingListItem.objects.get(
            reading_list=self.reading_list, book=self.book
        )
        self.assertEqual(item.added_by, self.member)

    def test_list_can_be_filtered_by_reading_list_id(self):
        ReadingListItem.objects.create(
            reading_list=self.reading_list, book=self.book, added_by=self.member
        )
        other_list = ReadingList.objects.create(name="Other", created_by=self.owner)
        other_book = Book.objects.create(title="1984", year=1949)
        ReadingListItem.objects.create(
            reading_list=other_list, book=other_book, added_by=self.owner
        )

        response = self.client.get(
            reverse("clubs:api-reading-list-item-list"),
            {"reading_list_id": self.reading_list.pk},
        )

        self.assertEqual(len(response.data), 1)


class ReadingListItemRowViewTests(TestCase):
    # Regression coverage: the personal-list branch of this view's old
    # hand-rolled dispatch() referenced reading_list_item.created_by, but
    # ReadingListItem has no such field (only added_by) - ReadingList does.
    # Any request against a personal list's item raised an unhandled
    # AttributeError (500). Fixed by moving onto ReadingListAccessRequiredMixin,
    # which correctly checks the reading list's created_by.
    def setUp(self):
        self.creator = make_user("creator@example.com")
        self.other_user = make_user("other@example.com")
        self.reading_list = ReadingList.objects.create(
            name="My List", created_by=self.creator
        )
        self.book = Book.objects.create(title="Dune", year=1965)
        self.item = ReadingListItem.objects.create(
            reading_list=self.reading_list, book=self.book, added_by=self.creator
        )

    def test_creator_can_view_personal_list_item_row(self):
        self.client.force_login(self.creator)

        response = self.client.get(
            reverse("clubs:reading-list-item-row", kwargs={"pk": self.item.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_non_creator_forbidden_from_personal_list_item_row(self):
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse("clubs:reading-list-item-row", kwargs={"pk": self.item.pk})
        )

        self.assertEqual(response.status_code, 403)
