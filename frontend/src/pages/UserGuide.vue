<template>
<q-page padding>
  <q-card>
    <q-card-section>
      <q-markdown>
User Guide
==========

## Data types

### Orders

An order is intended to correspond to one order to a facility with a responsible PI. If the PI changes, it should be considered as a new order.

Orders are considered to be "internal" data, and will thus only be visible to the users listed as `editors`.

One order can generate one or more datasets.


### Datasets

A dataset is a data release from an order. Thus, all datasets are associated with *one* specific order.

The data author, generator, and data manager is considered to be the same as for the associated order.


### Collections

Collections are intended to link together data from different orders, for example if the same project has received data from multiple projects.

Any user can associate any dataset with any collection.


## Using the Website

The website by default lists all available datasets and collections. 

### User

Users can log in using OpenID Connect or, if they already have an account, AuthID and API key.

Some information about the current user, e.g. affiliation and contact information, can be set by choosing "Current User" in the menu.

By default, newly logged in users can create collections, but they may also apply for permission to e.g. create orders.

### Creating a new entry

A new entry can be created by going to the browser page of the entry type (e.g. [collections](/collections/) or [datasets](/datasets/)) and clicking the "+" sign.

#### Order

Creating an order requires that you have the `ORDERS` permission. If you can view the order browser, you should have this permission.

### Generating an API key


## Using the API

The documentation is available on [Github](https://scilifelabdatacentre.github.io/Data-Tracker/).

You can get an API key that can be used for accessing the API.
      </q-markdown>
    </q-card-section>
  </q-card>
</q-page>
</template>

<script>
export default {
  name: 'UserGuide',
}
</script>