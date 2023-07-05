'''
Created on Jun 29, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''
from amaranth_testbench.examples.counter import ControlledCounter

from amaranth import Signal, Module
from amaranth import ResetSignal # ClockDomain, ClockSignal, 

if __name__ == "__main__":
    # allow us to run this directly
    from amaranth.asserts import Assert, Cover, Assume
    from amaranth.sim import Delay, Tick
    from amaranth_testbench.cli import CLI, main
    from amaranth_testbench.simulator import Simulator
    from amaranth_testbench.verification import Verification
    from amaranth_testbench.history import History
    
    
    MaxCountValue = 16
    cli = CLI.get()
    m = Module() # top level
    m.submodules.counter = dut = ControlledCounter(MaxCountValue)
    
    rst = Signal()
    m.d.comb += ResetSignal().eq(rst)
    m.d.comb += [
        Assume(~rst), # don't play with reset
    ]
    
    # create a history instance and keep track 
    # off all the public signals (enable, resetcount and count)
    # NOTE: numCyclesToTrack MUST be > than the check depth for this to work.
    hist = History.new(m, numCyclesToTrack=100)
    hist.trackAll(dut.ports())
    
    
        
    @Simulator.simulate(m, 'count_up', traces=dut.ports())
    def countUp():
        yield dut.resetcount.eq(1)
        yield Tick()
        yield dut.resetcount.eq(0)
        yield Delay(5e-6)
        yield dut.enable.eq(1)
        yield Delay((4 + (MaxCountValue*2))*1e-6)
        
        
        
    # this simulation will only occur if module was run with 'simulate' action
    @Simulator.simulate(m, 'count_and_resetcount', traces=dut.ports())
    def countAndresetcount():
        yield Delay(5e-6)
        yield dut.enable.eq(1)
        yield Delay(10e-6)
        yield dut.enable.eq(0)
        yield Delay(5e-6)
        yield dut.enable.eq(1)
        yield Delay(5e-6)
        yield dut.resetcount.eq(1)
        yield Delay(10e-6)
        yield dut.resetcount.eq(0)
        yield Delay((4 + (MaxCountValue*2))*1e-6)
        
        
    @Verification.coverAndVerify(m, dut)
    def noOverflow(m:Module, counter:ControlledCounter, includeCovers:bool=False):
        # no matter what, counter never exceeds max
        m.d.comb += Assert(counter.count <= counter.max)
    
    
    @Verification.coverAndVerify(m, dut)
    def resetcountAndCountForward(m:Module, counter:ControlledCounter, includeCovers:bool=False):
        
        # check what happens coming out of resetcount
        with m.If(hist.fell(counter.resetcount)):
            # we were just in resetcount but no longer, 
            m.d.comb += Assert(counter.count == 0)
            
        
        # if we let the system run max count ticks, while enable is asserted the whole time
        # and resetcount is not, then at each step the count will increment along with the 
        # system clock
        with m.If(hist.cycle == counter.max):
            with m.If(hist.isConstant(counter.enable, 1, startCycle=0, numCycles=counter.max) & 
                      hist.isConstant(counter.resetcount, 0, startCycle=0, numCycles=counter.max)):
                for ago in range(1,counter.max-1):
                    m.d.comb += Assert(hist.past(counter.count, stepsAgo=ago) == (counter.count-ago))
                    
                @Verification.depthProbe
                def dp(): # only active with --depthprobe
                    m.d.comb += Cover(counter.count == counter.max)
        
        
        with m.If(hist.isConstant(counter.resetcount, 0, startCycle=0, numCycles=counter.max)
                  &
                  hist.isConstant(counter.enable, 1, startCycle=0, numCycles=counter.max)):
            
            m.d.comb += Cover(counter.count == 8)
        
        
        
    @Verification.coverAndVerify(m, dut)
    def sequencesAndDepth(m:Module, counter:ControlledCounter, includeCovers:bool=False):

        # if resetcount goes _-_____...
        #   resetcount started at 0 then went high:
        with m.If(hist.followsSequence(counter.resetcount, [0,1])):
            #  then resetcount stayed at 0 for at least 15 cycles:
            with m.If(hist.isConstant(counter.resetcount, value=0, startCycle=2, numCycles=15)):
                # and enable goes __-----------...
                #  so 0 for 2 cycles, then 1:
                with m.If(hist.followsSequence(counter.enable, [0,0,1])):
                    #  and then stays high for at least 15 cycles
                    with m.If(hist.isConstant(counter.enable, value=1, startCycle=3, numCycles=15)):
                
                        # assert that, under these sets of conditions, 
                        # on cycle 10 the count will be 8
                        m.d.comb += Assert(hist.valueAt(counter.count, 10) == 8)
                        
                        # ensure this deep level of conditions is actually reached using
                        # --depthprobe when generating il
                        @Verification.depthProbe
                        def dp():
                            m.d.comb += Cover(counter.count == 8)
                            
        if includeCovers:
            
            # simply find some way to get to the max counter value
            m.d.comb += Cover(counter.count == counter.max)
            
            # find another occasion where we get to max value, 
            # however we want it to be less straightforward that 
            # just counting up to max in one go...
            with m.If(hist.cycle > (counter.max + 4)):
                m.d.comb += Cover(counter.count == counter.max)
                
                
            with m.If(hist.valueAt(counter.resetcount, 4) == 1):
                with m.If(hist.valueAt(counter.enable, 6) == 0):
                    m.d.comb += Cover(counter.count == 5)
                    
                    
                    
        
    @Verification.coverAndVerify(m, dut)
    def coverPast(m:Module, counter:ControlledCounter, includeCovers:bool=False):
        histInst2 = History.new(m, numCyclesToTrack=hist.numCyclesToTrack, 
                                name='simple_history')
        histInst2.trackAll(dut.ports())
    
        if includeCovers:
            m.d.comb += Cover(
                                (histInst2.cycle > 20)
                              & (histInst2.valueAt(counter.count, 4) == 2)
                              & (histInst2.valueAt(counter.count, 12) == 5)
                            )
                    
                    
            
    
    main(m, ports=dut.ports())