import logging

import tornado.web
import tornado

import db
import handlers
import utils

from peewee import fn, JOIN


class CountryList(handlers.UnsafeHandler):
    def get(self):
        self.write({'countries': [{'name': c} for c in self.country_list]})

    @property
    def country_list(self):
        return ["Afghanistan", "Albania", "Algeria", "American Samoa", "Andorra",
                "Angola", "Anguilla", "Antarctica", "Antigua and Barbuda",
                "Argentina", "Armenia", "Aruba", "Australia", "Austria",
                "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados",
                "Belarus", "Belgium", "Belize", "Benin", "Bermuda", "Bhutan",
                "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil",
                "British Indian Ocean Territory", "British Virgin Islands",
                "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia",
                "Cameroon", "Canada", "Cape Verde", "Cayman Islands",
                "Central African Republic", "Chad", "Chile", "China",
                "Christmas Island", "Cocos Islands", "Colombia", "Comoros",
                "Cook Islands", "Costa Rica", "Croatia", "Cuba", "Curacao",
                "Cyprus", "Czech Republic", "Democratic Republic of the Congo",
                "Denmark", "Djibouti", "Dominica", "Dominican Republic",
                "East Timor", "Ecuador", "Egypt", "El Salvador",
                "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia",
                "Falkland Islands", "Faroe Islands", "Fiji", "Finland", "France",
                "French Polynesia", "Gabon", "Gambia", "Georgia", "Germany",
                "Ghana", "Gibraltar", "Greece", "Greenland", "Grenada", "Guam",
                "Guatemala", "Guernsey", "Guinea", "Guinea-Bissau", "Guyana",
                "Haiti", "Honduras", "Hong Kong", "Hungary", "Iceland", "India",
                "Indonesia", "Iran", "Iraq", "Ireland", "Isle of Man", "Israel",
                "Italy", "Ivory Coast", "Jamaica", "Japan", "Jersey", "Jordan",
                "Kazakhstan", "Kenya", "Kiribati", "Kosovo", "Kuwait",
                "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia",
                "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Macau",
                "Macedonia", "Madagascar", "Malawi", "Malaysia", "Maldives",
                "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius",
                "Mayotte", "Mexico", "Micronesia", "Moldova", "Monaco",
                "Mongolia", "Montenegro", "Montserrat", "Morocco", "Mozambique",
                "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands",
                "Netherlands Antilles", "New Caledonia", "New Zealand",
                "Nicaragua", "Niger", "Nigeria", "Niue", "North Korea",
                "Northern Mariana Islands", "Norway", "Oman", "Pakistan", "Palau",
                "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
                "Philippines", "Pitcairn", "Poland", "Portugal", "Puerto Rico",
                "Qatar", "Republic of the Congo", "Reunion", "Romania", "Russia",
                "Rwanda", "Saint Barthelemy", "Saint Helena",
                "Saint Kitts and Nevis", "Saint Lucia", "Saint Martin",
                "Saint Pierre and Miquelon",
                "Saint Vincent and the Grenadines", "Samoa", "San Marino",
                "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia",
                "Seychelles", "Sierra Leone", "Singapore", "Sint Maarten",
                "Slovakia", "Slovenia", "Solomon Islands", "Somalia",
                "South Africa", "South Korea", "South Sudan", "Spain",
                "Sri Lanka", "Sudan", "Suriname", "Svalbard and Jan Mayen",
                "Swaziland", "Sweden", "Switzerland", "Syria", "Taiwan",
                "Tajikistan", "Tanzania", "Thailand", "Togo", "Tokelau", "Tonga",
                "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
                "Turks and Caicos Islands", "Tuvalu", "U.S. Virgin Islands",
                "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom",
                "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican",
                "Venezuela", "Vietnam", "Wallis and Futuna", "Western Sahara",
                "Yemen", "Zambia", "Zimbabwe"]


class GetDataset(handlers.UnsafeHandler):
    def get(self, ds_identifier):
        user = self.current_user

        try:
            dbid = int(ds_identifier)
            try:
                dataset = db.Dataset.get_by_id(dbid)
            except db.Dataset.DoesNotExist:
                self.send_error(status_code=404)
                return
        except ValueError:
            self.send_error(status_code=400, reason='Dataset id should be an integer')
            return

        if not dataset.visible and not (utils.has_rights(user, ('Steward', 'Admin'))
                                        or utils.is_owner(user, dataset)):
            self.send_error(status_code=403)
            return

        dataset = db.build_dict_from_row(dataset)
        dataset['tags'] = [entry for entry in (db.DatasetTag
                                               .select(db.Tag)
                                               .join(db.Tag)
                                               .where(db.DatasetTag.dataset == dbid)
                                               .dicts())]

        dataset['publications'] = [entry for entry in (db.DatasetPublication
                                                       .select(db.Publication)
                                                       .join(db.Publication)
                                                       .where(db.DatasetPublication.dataset == dbid)
                                                       .dicts())]

        dataset['data_urls'] = [entry for entry in (db.DatasetDataUrl
                                                    .select(db.DataUrl)
                                                    .join(db.DataUrl)
                                                    .where(db.DatasetDataUrl.dataset == dbid)
                                                    .dicts())]
        self.finish(dataset)


class GetUser(handlers.UnsafeHandler):
    """Retrieve basic information about the current user."""
    def get(self):
        user = self.current_user

        ret = {'user': None, 'email': None}
        if user:
            ret = {'user': user.name,
                   'email': user.email,
                   'affiliation': user.affiliation,
                   'country': user.country}

        self.finish(ret)


class ListDatasets(handlers.UnsafeHandler):
    def get(self):
        user = self.current_user

        if utils.has_rights(user, ('Steward', 'Admin')):
            ret = [dataset for dataset in (db.Dataset
                                           .select(db.Dataset.id, db.Dataset.title)
                                           .dicts())]
        else:
            ret = [dataset for dataset in (db.Dataset
                                           .select(fn.Distinct(db.Dataset.id), db.Dataset.title)
                                           .join(db.DatasetOwner, JOIN.LEFT_OUTER)
                                           .where((db.Dataset.visible==True) |
                                                  (db.DatasetOwner.user == user))
                                           .dicts())]

        self.finish({'datasets': ret})


class ListUsers(handlers.AdminHandler):
    """Retrieve a list of all users, including permissions etc."""
    def get(self):
        users = [user for user in db.User.select().dicts()]
        self.finish({'users': users})


class QuitHandler(handlers.UnsafeHandler):
    def get(self):  # pylint: disable=no-self-use
        ioloop = tornado.ioloop.IOLoop.instance()
        ioloop.stop()
