<template>
<q-page padding>
  <h2 class="text-capitalize">{{ entryType + 's' }}</h2>
  <q-card>
    <q-card-section>
  <q-table
    :data="entries"
    :columns="columns"
    row-key="id"
    :pagination.sync="pagination"
    :filter="filter"
    grid
    :loading="loading"
    no-data-label="No entries found"
    :no-results-label="filter + ' does not match any entries'">

    <template v-slot:top-left>
      <q-btn v-show="showAdd"
             round
             color="primary"
             icon="add"
             :to="{ 'name': pageNew }" />
    </template>

    <template v-slot:top-right>
      <q-input rounded
               outlined
               dense
               debounce="300"
               v-model="filter"
               placeholder="Search">
        <template v-slot:append>
          <q-icon name="search" />
        </template>
      </q-input>
    </template>

    <template v-slot:item="props">
      <div class="col-xs-12 col-md-6 col-lg-4 col-xl-3 row self-stretch">
        <q-card class="q-ma-xs bg-grey-2 col" @click="gotoEntry(props.row._id)">
          <q-card-section class="text-center">
            <div class="text-h6 bg-grey-4 q-mb-xs q-pa-xs">
              {{ props.row.title }}
            </div>
            <div class="text-caption">
              {{ props.row._id }}
            </div>
          </q-card-section>
          <q-card-section>
            <q-chip square
                    color="grey-3"
                    v-for="field in Object.keys(props.row.properties)"
                    :key="field">
              <span class="text-bold text-capitalize text-blue-9 q-mr-sm">{{ field }}</span> {{ props.row.properties[field] }}
            </q-chip>
            <q-chip square
                    color="grey-3"
                    v-for="entry in props.row.tags"
                    :key="entry">
              <q-avatar color="secondary" text-color="white" icon="fas fa-tag" />
              {{ entry }}
            </q-chip>
          </q-card-section>
        </q-card>
      </div>
    </template>
  </q-table>
    </q-card-section>
  </q-card>
</q-page>
</template>

<script>
import { format } from 'quasar'
const { capitalize } = format

export default {
  name: 'EntryBrowser',

  computed: {
    entries: {
      get () {
        return this.$store.state.entries.entryList;
      },
    },

    showAdd: {
      get () {
        let passed = false;
        if (this.entryType === 'datasets' && this.currentUser.permissions.includes('ORDERS'))
          passed = true;
        else if (this.currentUser.email !== '')
          passed = true;
        return passed;
      }
    },

    currentUser: {
      get () {
        return this.$store.state.currentUser.info;
      },
    },
  },

  props: {
    entryType: {
      type: String,
      required: true
    }
  },

  watch: {
    entryType: {
      immediate: true,
      handler () {
        this.loadData();
      }
    }
  },
  
  data () {
    return {
      filter: '',
      pageAbout: '',
      pageNew: '',
      loading: true,
      pagination: {
        rowsPerPage: 20
      },
      columns: [
        {
          name: 'id',
          label: 'Identifier (UUID)',
          field: '_id',
          required: true,
          align: 'left',
          sortable: true,
        },
        {
          name: 'title',
          label: 'Order title',
          field: 'title',
          required: true,
          sortable: true
        },
        {
          name: 'properties',
          label: 'Properties',
          field: 'properties',
          required: false,
          sortable: false
        },
        {
          name: 'tags',
          label: 'Tags',
          field: 'tags',
          required: false,
          sortable: false
        }
      ]
    }
  },

  methods: {
    gotoEntry (uuid) {
      this.$router.push({ name: this.pageAbout, params: { 'uuid': uuid } });
    },
    loadData () {
      this.$store.dispatch('entries/resetEntryList')
        .then(() => this.loading = true)
        .then(() => {
          this.$store.dispatch('entries/getEntries', this.entryType)
            .then(() => this.loading = false)
            .catch(() => this.loading = false)
        });
      this.pageAbout = capitalize(this.entryType) + ' About';
      this.pageNew = capitalize(this.entryType) + ' New';
    },
  }
}
</script>
