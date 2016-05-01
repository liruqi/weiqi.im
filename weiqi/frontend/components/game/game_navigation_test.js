import Vue from 'vue';
import { setupTest } from './../../test/utils';
import { createGame } from './../../test/fixtures';

setupTest();

describe('game_navigation.vue', function() {
    function getComponent() {
        return new Vue({
            components: {'qi-nav': require('./game_navigation.vue')},
            template: '<div><qi-nav v-ref:component :game="game" :is-player="isPlayer" :has-control="hasControl" '
                + ':force_node_id.sync="force_node_id"></qi-nav></div>',
            data() {
                return {
                    game: createGame(),
                    isPlayer: false,
                    hasControl: false,
                    force_node_id: false
                }
            }
        }).$mount();
    }

    it('should render correctly', function() {
        var vm = getComponent();
        expect(vm.$el.querySelectorAll('.game-nav-node-label').length).toBe(3);
    });

    describe('back-to-game button', function() {
        var tests = [
            ['normal game', false, false, false, true],
            ['demo spectator', true, false, false, true],
            ['demo controller', true, false, true, false]
        ];

        tests.forEach(function(test) {
            it('should show correctly: '+test[0], function (done) {
                var vm = getComponent();
                var comp = vm.$refs.component;

                vm.game.is_demo = test[1];
                vm.isPlayer = test[2];
                vm.hasControl = test[3];

                comp.$nextTick(function () {
                    if(test[4]) {
                        expect(comp.$els.backToGame).toBeTruthy();
                    } else {
                        expect(comp.$els.backToGame).toBeFalsy();
                    }
                    done();
                });
            });
        });
    });
});