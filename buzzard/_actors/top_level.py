import collections
import itertools

from buzzard._actors.message import Msg
from buzzard._actors.pool_waiting_room import ActorPoolWaitingRoom
from buzzard._actors.pool_working_room import ActorPoolWorkingRoom
from buzzard._actors.global_priorities_watcher import ActorGlobalPrioritiesWatcher

class ActorTopLevel(object):
    """Actor that takes care of the lifetime of all other actors.

    That is the only actor that is instanciated by the scheduler. All other actors are
    instanciated here.
    """
    def __init__(self):
        self._rasters = set()
        self._rasters_per_pool = collections.defaultdict(list)

        self._actor_addresses_of_raster = {}
        self._actor_addresses_of_pool = {}

        self._primed = False
        self._alive = True

    address = '/Global/TopLevel'

    @property
    def alive(self):
        return self._alive

    # ******************************************************************************************* **
    def ext_receive_prime(self):
        """Receive message sent by something else than an actor, still treated synchronously: Prime
        yourself, we are about to start the show!
        """
        assert not self._primed
        self._primed = True
        return [
            ActorGlobalPrioritiesWatcher()
        ]

    def ext_receive_new_raster(self, raster):
        """Receive message sent by something else than an actor, still treated synchronously: There
        is a new raster

        Parameter
        ---------
        raster: _a_recipe_raster.ABackRecipeRaster
        """
        msgs = []
        self._rasters.add(raster)

        # Instanciate raster's actors ******************************************
        actors = raster.create_actors()
        msgs += actors
        self._actor_addresses_of_raster[raster] = [
            actor.address
            for actor in actors
        ]
        del actors

        # Instanciate pools' actors ********************************************
        pools = {
            id(pool): pool
            for attr in [
                'computation_pool', 'merge_pool', 'io_pool', 'resample_pool',
            ]
            if hasattr(raster, attr)
            for pool in [getattr(raster, attr)]
            if pool is not None
        }
        for pool_id, pool in pools.items():
            if pool_id not in self._rasters_per_pool:
                actors = [
                    ActorPoolWaitingRoom(pool),
                    ActorPoolWorkingRoom(pool),
                ]
                msgs += actors

                self._actor_addresses_of_pool[pool_id] = [
                    actor.address
                    for actor in actors
                ]

            self._rasters_per_pool[pool_id].append(raster)

        return msgs

    def ext_receive_kill_raster(self, raster):
        """Receive message sent by something else than an actor, still treated synchronously: An
        actor is closing

        Parameter
        ---------
        raster: _a_recipe_raster.ABackRecipeRaster
        """
        msgs = []
        self._rasters.remove(raster)

        # Deleting raster's actors *********************************************
        msgs += [
            Msg(address, 'die')
            for address in self._actor_addresses_of_raster[raster]
        ]
        del self._actor_addresses_of_raster[raster]

        # Deleting pools' actors ***********************************************
        pools = {
            id(pool): pool
            for attr in [
                'computation_pool', 'merge_pool', 'write_pool',
                'file_checker_pool', 'read_pool', 'resample_pool',
            ]
            if hasattr(raster, attr)
            for pool in [getattr(raster, attr)]
        }
        for pool_id, pool in pools.items():
            self._rasters_per_pool[pool_id].remove(raster)
            if len(self._rasters_per_pool) == 0:
                del self._rasters_per_pool[pool_id]
                msgs += [
                    Msg(actor.address, 'die')
                    for actor in self._actor_addresses_of_pool[pool_id]
                ]
                del self._actor_addresses_of_pool[pool_id]

        return msgs

    def ext_receive_die(self):
        """Receive message sent by something else than an actor, still treated synchronously: The
        DataSource is closing
        """
        assert self._alive
        self._alive = False

        msgs = [
            Msg(address, 'die')
            for address in itertools.chain(
                itertools.chain.from_iterable(self._actor_addresses_of_raster.values()),
                itertools.chain.from_iterable(self._actor_addresses_of_pool.values()),
            )
        ] + [Msg('/GlobalPrioritiesWatcher', 'die')]

        # Clear attributes *****************************************************
        self._rasters.clear()
        self._rasters_per_pool.clear()
        self._actor_addresses_of_raster.clear()
        self._actor_addresses_of_pool.clear()

        return []

    # ******************************************************************************************* **
