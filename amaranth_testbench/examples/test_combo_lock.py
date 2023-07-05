'''
Created on Jul 3, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''

from amaranth import Module
from amaranth.asserts import Assert, Cover

from amaranth_testbench.examples.combo_lock import ComboLock, KEY1, KEY2

if __name__ == "__main__":
    # allow us to run this directly
    from amaranth_testbench.cli import CLI, main
    from amaranth_testbench.simulator import Simulator
    from amaranth_testbench.verification import Verification
    from amaranth_testbench.history import History
    
    cli = CLI.get()
    m = Module() # top level
    m.submodules.combolock = dut = ComboLock()
        
    @Verification.coverAndVerify(m, dut)
    def coverAndVerify(m:Module, combolock:ComboLock, includeCovers:bool=False):
        # Note: I have a condition below that makes the period 0.1s -- so 
        # during testing we only need to count a bit past 100 ticks to see results
        hist = History.new(m, numCyclesToTrack=30)
        hist.track(combolock.input)
        hist.track(combolock.opened)
        
        
        # if we _ever_ have key1, followed by key2, followed by 0 the lock is open
        with m.If(hist.pastSequenceWas(combolock.input, [KEY1, KEY2, 0])):
            m.d.comb += Assert(combolock.opened)
        
        # if we ever have key1 three cycles ago, and key2 two cycles ago, opened
        # this case covers the above, and any input subsequent to key2
        with m.If( (hist.past(combolock.input, 3) == KEY1) 
                &
                    (hist.past(combolock.input,2) == KEY2)
                ):
            m.d.comb += Assert(combolock.opened)
            
            
            
            
        with m.If(hist.isEver(combolock.opened, 1, numCycles=10)):
            # it was open by tick 10, it is open forever after
            m.d.comb += Assert(combolock.opened)
            
            m.d.comb += Assert(
                hist.isEver(combolock.input, KEY1, numCycles=12)
                &
                hist.isEver(combolock.input, KEY2, numCycles=11)
                )
            
            # if the lock just opened one step back in the past
            with m.If(hist.pastSequenceWas(combolock.opened, [0,1])):
                # then 2 steps back it was key2 and before that it was key1
                m.d.comb += Assert(
                    (hist.past(combolock.input, 2) == KEY2)
                    &
                    (hist.past(combolock.input, 3) == KEY1)
                    )
                
                @Verification.depthProbe
                def dpA(): # only active with --depthprobe
                    m.d.comb += Cover(hist.past(combolock.input, 3) == KEY1)
        
        
        # when it is just opened, it is because Key2 followed immediately after key1
        with m.If(hist.rose(combolock.opened)):
            # so the two steps before that had the combo, in order
            m.d.comb += Assert(
                    (hist.past(combolock.input, 2) == KEY1 )
                    &
                    (hist.past(combolock.input, 1) == KEY2 )
                )
            
            @Verification.depthProbe
            def dpB(): # only active with --depthprobe
                m.d.comb += Cover(
                    (hist.past(combolock.input, 2) == KEY1 )
                    &
                    (hist.past(combolock.input, 1) == KEY2 ))
    
        
        
        
        # if on tick 2 we get key1 and on tick 3 we get key2
        # we are now (and forever after) unlocked
        with m.If(hist.valueAt(combolock.input, 2) == KEY1):
            with m.If(hist.valueAt(combolock.input, 3) == KEY2):
                m.d.sync += Assert(combolock.opened)
            
            @Verification.depthProbe
            def dpC(): # only active with --depthprobe
                m.d.comb += Cover(combolock.opened)
                    
                    
        if includeCovers:
            m.d.comb += Cover(
                    (hist.pastSequenceWas(combolock.input, [5,4,3,2,1]))
                    &
                    combolock.opened
                )
            
            # force it to find a way to open lock, indirectly
            with m.If(hist.followsSequence(combolock.opened, values=[0,0,0,0,0,0,0,0,0,1])):
                m.d.comb += Cover(hist.valueAt(combolock.input, 6) == 0xAA)
                
            # force to find way to open but also to feed it some (invalid) input first
            with m.If(hist.followsSequence(combolock.input, values=[5,4,3,2,1,0])):
                # and continue for a while
                with m.If(hist.cycle > 10):
                    m.d.comb += Cover(combolock.opened)
                    
                    
                    
                    
    # this simulation will only occur if module was run with 'simulate' action
    @Simulator.simulate(m, 'combolock_openit', traces=[dut.input, dut.opened])
    def unlockAfterFail():
        yield from Simulator.setAndTick(dut.input, 0xde)
        yield from Simulator.setAndTick(dut.input, KEY1)
        yield from Simulator.setAndTick(dut.input, 0xde)
        yield from Simulator.setAndTick(dut.input, KEY2)
        yield from Simulator.setAndTick(dut.input, 0xad)
        yield from Simulator.setAndTick(dut.input, KEY1) # still closed
        yield from Simulator.setAndTick(dut.input, KEY2) # opens
        yield from Simulator.setAndTick(dut.input, 0xde) # stays open
        yield from Simulator.setAndTick(dut.input, 0xad)
        
            
    
    main(m, ports=dut.ports())
