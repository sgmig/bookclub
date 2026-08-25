from datetime import timedelta
from types import SimpleNamespace

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

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
from clubs.permissions import IsClubMember
from locations.models import Location


def make_user(email):
    return CustomUser.objects.create_user(
        email=email, password="password123", first_name="First", last_name="Last"
    )


def make_club_with_member(
    name="Book Lovers", email="member@example.com", owner_email="owner@example.com"
):
    owner = make_user(owner_email)
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

        club_location = Location.objects.create(
            name="Library", address="1 Book Rd", is_private=False
        )
        ClubLocation.objects.create(club=club, location=club_location)

        unrelated_location = Location.objects.create(
            name="Unrelated Cafe", address="2 Coffee Rd", is_private=False
        )
        ClubLocation.objects.create(club=other_club, location=unrelated_location)

        form = ClubMeetingForm(club=club)

        self.assertIn(club_location, form.fields["location"].queryset)
        self.assertNotIn(unrelated_location, form.fields["location"].queryset)

    def test_redacted_private_location_excluded_from_choices(self):
        club, member, owner = make_club_with_member()

        redacted_location = Location.objects.create(
            name="Jane's Place", address="", is_private=True, created_by=member
        )
        ClubLocation.objects.create(club=club, location=redacted_location)

        still_usable_location = Location.objects.create(
            name="Library", address="1 Book Rd", is_private=False
        )
        ClubLocation.objects.create(club=club, location=still_usable_location)

        form = ClubMeetingForm(club=club)

        self.assertNotIn(redacted_location, form.fields["location"].queryset)
        self.assertIn(still_usable_location, form.fields["location"].queryset)


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


class ReadingListItemAPIPermissionTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")
        self.club_list = ReadingList.objects.create(
            name="Club list", club=self.club, created_by=self.owner
        )
        self.personal_list = ReadingList.objects.create(
            name="Personal list", created_by=self.owner
        )
        self.book = Book.objects.create(title="Dune", year=1965)
        self.club_item = ReadingListItem.objects.create(
            reading_list=self.club_list, book=self.book, added_by=self.owner
        )
        self.personal_item = ReadingListItem.objects.create(
            reading_list=self.personal_list, book=self.book, added_by=self.owner
        )

    def test_non_member_cannot_create_item_in_club_list(self):
        self.client.force_login(self.outsider)
        other_book = Book.objects.create(title="1984", year=1949)

        response = self.client.post(
            reverse("clubs:api-reading-list-item-list"),
            {"reading_list": self.club_list.pk, "book": other_book.pk},
        )

        self.assertEqual(response.status_code, 403)

    def test_non_creator_cannot_create_item_in_personal_list(self):
        self.client.force_login(self.member)
        other_book = Book.objects.create(title="1984", year=1949)

        response = self.client.post(
            reverse("clubs:api-reading-list-item-list"),
            {"reading_list": self.personal_list.pk, "book": other_book.pk},
        )

        self.assertEqual(response.status_code, 403)

    def test_creator_can_create_item_in_personal_list(self):
        self.client.force_login(self.owner)
        other_book = Book.objects.create(title="1984", year=1949)

        response = self.client.post(
            reverse("clubs:api-reading-list-item-list"),
            {"reading_list": self.personal_list.pk, "book": other_book.pk},
        )

        self.assertEqual(response.status_code, 201)

    def test_non_member_cannot_retrieve_club_item(self):
        # 404, not 403: get_queryset() is scoped to accessible items, so a
        # non-member's request never finds the object at all (via DRF's
        # get_object_or_404 against that scoped queryset) - which happens
        # before has_object_permission ever runs. This is arguably better
        # than a 403 here: it doesn't confirm to a non-member that the
        # object exists at all.
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse(
                "clubs:api-reading-list-item-detail", kwargs={"pk": self.club_item.pk}
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_non_member_cannot_delete_club_item(self):
        self.client.force_login(self.outsider)

        response = self.client.delete(
            reverse(
                "clubs:api-reading-list-item-detail", kwargs={"pk": self.club_item.pk}
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ReadingListItem.objects.filter(pk=self.club_item.pk).exists())

    def test_member_can_delete_club_item(self):
        self.client.force_login(self.member)

        response = self.client.delete(
            reverse(
                "clubs:api-reading-list-item-detail", kwargs={"pk": self.club_item.pk}
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ReadingListItem.objects.filter(pk=self.club_item.pk).exists())

    def test_list_only_returns_accessible_items(self):
        # outsider is neither a club member nor the personal list's creator,
        # so `list` should return neither item - not even the club one,
        # which used to be fully enumerable by any authenticated user.
        self.client.force_login(self.outsider)

        response = self.client.get(reverse("clubs:api-reading-list-item-list"))

        returned_ids = {row["id"] for row in response.data}
        self.assertNotIn(self.club_item.pk, returned_ids)
        self.assertNotIn(self.personal_item.pk, returned_ids)

    def test_list_returns_items_from_own_club_and_personal_lists(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("clubs:api-reading-list-item-list"))

        returned_ids = {row["id"] for row in response.data}
        self.assertIn(self.club_item.pk, returned_ids)
        self.assertIn(self.personal_item.pk, returned_ids)


class ClubMeetingAPIPermissionTests(TestCase):
    # NOTE: ClubMeetingSerializer nests `location` and `discussed_books` as
    # writable-by-default nested serializers with no create()/update()
    # override on the serializer or the viewset. This means POST/PUT/PATCH
    # against this endpoint already raised an AssertionError
    # ("`.create()` method does not support writable nested fields") before
    # this permissions work, and still does - a pre-existing, unrelated bug,
    # confirmed empirically while writing these tests and left unfixed here
    # (see docs/PERMISSIONS_DESIGN.md). So `create`/`update` permission
    # denial is tested directly (which happens before serializer validation
    # and is unaffected by that bug), and the "member is allowed" side of
    # `create` is tested against the permission class in isolation rather
    # than via a full POST, since a full POST can't succeed today
    # regardless of permissions.
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.other_club, self.other_member, _ = make_club_with_member(
            name="Other Club",
            email="other-member@example.com",
            owner_email="other-owner@example.com",
        )
        self.outsider = make_user("outsider@example.com")
        self.location = Location.objects.create(name="Library")
        self.meeting = ClubMeeting.objects.create(
            club=self.club, location=self.location, date=timezone.now()
        )
        self.other_meeting = ClubMeeting.objects.create(
            club=self.other_club, location=self.location, date=timezone.now()
        )

    def test_member_can_retrieve_meeting(self):
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("clubs:api-club-meeting-detail", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_non_member_cannot_retrieve_meeting(self):
        # 404, not 403: same reasoning as ReadingListItemAPIPermissionTests
        # above - get_queryset() is scoped to the user's own clubs, so a
        # non-member's request never finds the object via the scoped
        # get_object_or_404 lookup, before has_object_permission runs.
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse("clubs:api-club-meeting-detail", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_non_member_cannot_delete_meeting(self):
        self.client.force_login(self.outsider)

        response = self.client.delete(
            reverse("clubs:api-club-meeting-detail", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ClubMeeting.objects.filter(pk=self.meeting.pk).exists())

    def test_member_can_delete_meeting(self):
        self.client.force_login(self.member)

        response = self.client.delete(
            reverse("clubs:api-club-meeting-detail", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ClubMeeting.objects.filter(pk=self.meeting.pk).exists())

    def test_non_member_cannot_create_meeting(self):
        self.client.force_login(self.outsider)

        response = self.client.post(
            reverse("clubs:api-club-meeting-list"),
            {"club": self.club.pk, "date": timezone.now().isoformat(), "notes": ""},
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_create_meeting(self):
        response = self.client.post(
            reverse("clubs:api-club-meeting-list"),
            {"club": self.club.pk, "date": timezone.now().isoformat(), "notes": ""},
        )

        self.assertEqual(response.status_code, 403)

    def test_list_only_returns_own_clubs_meetings(self):
        self.client.force_login(self.member)

        response = self.client.get(reverse("clubs:api-club-meeting-list"))

        returned_ids = {row["id"] for row in response.data}
        self.assertIn(self.meeting.pk, returned_ids)
        self.assertNotIn(self.other_meeting.pk, returned_ids)

    def test_list_club_id_filter_cannot_leak_other_clubs_meetings(self):
        # Passing another club's id shouldn't bypass the membership scoping.
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("clubs:api-club-meeting-list"), {"club_id": self.other_club.pk}
        )

        self.assertEqual(response.data, [])

    def _create_permission_request(self, user):
        # Request() built directly (not via APIView.initialize_request())
        # gets an empty parser list unless passed explicitly - without this
        # it can't parse the multipart body APIRequestFactory built. Its
        # `.user` is also a lazy property that re-authenticates from
        # self.authenticators (empty here, so it'd resolve to AnonymousUser)
        # rather than reading django_request.user - must go through the
        # Request's own `.user` setter instead, which correctly sets both.
        factory = APIRequestFactory()
        django_request = factory.post("/", {"club": self.club.pk})
        request = Request(django_request, parsers=[MultiPartParser(), FormParser()])
        request.user = user
        return request

    def test_permission_class_allows_member_to_create(self):
        # See class docstring: a full POST can't succeed today regardless
        # of permissions (unrelated pre-existing serializer bug), so the
        # "member is allowed" half of create permission is tested against
        # the permission class directly.
        request = self._create_permission_request(self.member)
        view = SimpleNamespace(action="create")

        self.assertTrue(IsClubMember().has_permission(request, view))

    def test_permission_class_denies_non_member_create(self):
        request = self._create_permission_request(self.outsider)
        view = SimpleNamespace(action="create")

        self.assertFalse(IsClubMember().has_permission(request, view))


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


class MembershipRedactionSignalTests(TestCase):
    # Tests clubs/signals.py, which calls Location.redact_for_departed_member()
    # on ClubMembership removal/deactivation. The classmethod itself is
    # tested directly in locations.tests.RedactForDepartedMemberTests.
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.location = Location.objects.create(
            name="Jane's Place",
            address="123 Main St",
            created_by=self.member,
            is_private=True,
        )
        ClubLocation.objects.create(club=self.club, location=self.location)

    def test_deleting_membership_triggers_redaction(self):
        ClubMembership.objects.get(user=self.member, club=self.club).delete()

        self.location.refresh_from_db()
        self.assertEqual(self.location.address, "")

    def test_deactivating_membership_triggers_redaction(self):
        membership = ClubMembership.objects.get(user=self.member, club=self.club)
        membership.is_active = False
        membership.save()

        self.location.refresh_from_db()
        self.assertEqual(self.location.address, "")

    def test_saving_without_deactivating_does_not_redact(self):
        membership = ClubMembership.objects.get(user=self.member, club=self.club)
        membership.is_admin = True
        membership.save()

        self.location.refresh_from_db()
        self.assertEqual(self.location.address, "123 Main St")

    def test_creating_a_new_membership_does_not_redact(self):
        outsider = make_user("outsider@example.com")
        # Creating a membership is a save() with created=True - must not be
        # mistaken for a deactivation.
        ClubMembership.objects.create(user=outsider, club=self.club)

        self.location.refresh_from_db()
        self.assertEqual(self.location.address, "123 Main St")

    def test_removing_membership_from_a_different_club_does_not_redact(self):
        other_club = Club.objects.create(name="Other Club", created_by=self.owner)
        other_membership = ClubMembership.objects.create(
            user=self.member, club=other_club
        )

        other_membership.delete()

        self.location.refresh_from_db()
        self.assertEqual(self.location.address, "123 Main St")


class LocationCreateModalViewTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")
        self.url = reverse(
            "clubs:location-create-modal", kwargs={"club_id": self.club.pk}
        )

    def test_member_can_load_modal(self):
        self.client.force_login(self.member)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_non_member_forbidden(self):
        self.client.force_login(self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class ClubLocationAPITests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")
        self.location = Location.objects.create(name="Member's Place", address="5 Home Rd")
        self.list_url = reverse("clubs:api-club-location-list")

    def test_member_can_link_a_location_to_their_club(self):
        self.client.force_login(self.member)

        response = self.client.post(
            self.list_url, {"club": self.club.pk, "location": self.location.pk}
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            ClubLocation.objects.filter(
                club=self.club, location=self.location
            ).exists()
        )

    def test_non_member_cannot_link_a_location_to_a_club(self):
        self.client.force_login(self.outsider)

        response = self.client.post(
            self.list_url, {"club": self.club.pk, "location": self.location.pk}
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            ClubLocation.objects.filter(
                club=self.club, location=self.location
            ).exists()
        )

    def test_anonymous_cannot_link_a_location_to_a_club(self):
        response = self.client.post(
            self.list_url, {"club": self.club.pk, "location": self.location.pk}
        )

        self.assertEqual(response.status_code, 403)

    def test_list_only_returns_own_clubs_locations(self):
        other_club, other_member, _ = make_club_with_member(
            name="Other Club",
            email="other-member@example.com",
            owner_email="other-owner@example.com",
        )
        other_location = Location.objects.create(name="Other Place")
        ClubLocation.objects.create(club=other_club, location=other_location)
        ClubLocation.objects.create(club=self.club, location=self.location)

        self.client.force_login(self.member)
        response = self.client.get(self.list_url)

        returned_location_ids = {row["location"]["id"] for row in response.data}
        self.assertIn(self.location.pk, returned_location_ids)
        self.assertNotIn(other_location.pk, returned_location_ids)

    def test_patch_does_not_crash_on_nested_location_field(self):
        # Regression test: ClubLocationSerializer.location is nested
        # (LocationSerializer), and is the fallback serializer for
        # update/partial_update. Without read_only=True on that field, a
        # PATCH including `location` would hit the same "doesn't support
        # writable nested fields" AssertionError as ClubMeetingSerializer.
        club_location = ClubLocation.objects.create(
            club=self.club, location=self.location
        )
        self.client.force_login(self.member)

        response = self.client.patch(
            reverse(
                "clubs:api-club-location-detail", kwargs={"pk": club_location.pk}
            ),
            {"location": self.location.pk},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
