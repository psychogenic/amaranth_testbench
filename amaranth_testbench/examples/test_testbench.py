'''
Created on Jul 1, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com


This is a very simple module that is used to put the testbench itself through 
it's paces.

The module has two inputs:
     * single bit enable
     * wide invalue
and two outputs:
    * single bit outflag, which mirrors enable
    * wide output, which mirrors invalue (upto and including a given max value)

A variety of tests are performed looking at the manner in which the test bench
tracks signal history and allows us to see (and force behaviour) related to
     * past signal values
     * sequences of signal behaviour
     * rise/fall detection

It also uses a great many @Verification.depthProbe methods to ensure 
coverage of the assertions made.


'''


from amaranth import Signal, Elaboratable, Module
from amaranth.build import Platform

from amaranth_testbench.verification import Verification


class TestBenchTest(Elaboratable):
    '''
        A simple counter that counts up to MAX and restarts at 0.
    '''
    
    def __init__(self, maxValue:int):
    
        bitlen = 8 # math.ceil(math.log2(maxValue))+1
        self.max = maxValue
        self.enable = Signal()
        self.invalue = Signal(bitlen)
        
        
        # output
        self.outflag = Signal()
        self.output = Signal(bitlen)
        
    def elaborate(self, platform:Platform):
        m = Module()
        
        m.d.sync += [
            
                self.output.eq(self.invalue),
                self.outflag.eq(self.enable)
            ]
        
        with m.If(self.invalue > self.max):
            m.d.sync += self.output.eq(self.max)
                    
        return m
    
    def ports(self):
        return [self.enable, self.invalue, self.outflag, self.output]
    


from amaranth import ResetSignal # ClockDomain, ClockSignal, 

if __name__ == "__main__":
    # allow us to run this directly
    from amaranth.asserts import Assert, Cover, Assume
    from amaranth_testbench.cli import CLI, main
    from amaranth_testbench.simulator import Simulator, Tick, Delay
    from amaranth_testbench.history import History
    
    MaxVal = 32
    cli = CLI.get()
    m = Module() # top level
    m.submodules.tb = dut = TestBenchTest(MaxVal)
    
    
    # create a history instance and keep track 
    # off all the public signals (enable, reset and count)
    # NOTE: numCyclesToTrack MUST be > than the check depth for this to work.
    hist = History.new(m, numCyclesToTrack=MaxVal * 2)
    hist.trackAll(dut.ports())
    
    rst = Signal()
    m.d.comb += ResetSignal().eq(rst)
    
    hist.track(rst)
    
        
    @Simulator.simulate(m, 'tb_toggling', traces=dut.ports())
    def toggles():
        yield Tick()
        yield dut.invalue.eq(4)
        yield dut.enable.eq(1)
        yield Delay(5e-6)
        yield dut.enable.eq(0)
        yield Delay(2e-6)
        yield dut.invalue.eq(dut.max + 5)
        yield Delay(4e-6)
        
        
        
    @Verification.coverAndVerify(m, dut)
    def noOverflow(m:Module, tb:TestBenchTest, includeCovers:bool=False):
        # no matter what, output never exceeds max
        m.d.comb += Assert(tb.output <= tb.max)
        
        if includeCovers:
            # some random cover with interesting looking events
            # we set the output and outflag to force the system to find 
            # how to twiddle the inputs
            m.d.comb += Cover( (tb.output == 15)
                               &
                               hist.pastSequenceWas(tb.output, [10, 11, 12, 13, 14])
                               &
                               ~(tb.outflag)
                               &
                               hist.pastTrue(tb.outflag, 3)
                               )
    
        
    @Verification.coverAndVerify(m, dut, group="risefall")
    def riseAndFall(m:Module, tb:TestBenchTest, includeCovers:bool=False):
        
        # if you rose, you can't have fallen
        with m.If(hist.rose(tb.enable)):
            m.d.comb += Assert(~(hist.fell(tb.enable)))
            
            # this implies a sequence ..._-
            #                             ^
            #                             now high
            # it's a single bit value, so our ~ will work as expected
            m.d.comb += Assert(~(hist.past(tb.enable)) & tb.enable)
            
            # pastTrue/pastFalse/valueTrue/ValueFalse works for any type of signal
            m.d.comb += Assert( hist.pastFalse(tb.enable) & hist.valueTrue(tb.enable))
            
            
            @Verification.depthProbe
            def dp1():
                m.d.comb += Cover(~(hist.fell(tb.enable)))
                
        
        # tb.outflag is a one-cycle-delayed mirror on tb.enable
        # so if it fell (meaning we just went low), then enable fell
        # 1 cycle ago
        with m.If(hist.fell(tb.outflag)):
            m.d.comb += Assert(hist.pastFell(tb.enable, 1))
            
            @Verification.depthProbe
            def dp2():
                m.d.comb += Cover(hist.fell(tb.outflag))
            
        # if our outflag went high, it means the enable was high
        with m.If(hist.rose(tb.outflag)):
            
            # however, solver may just start-up with the enable 
            # high, in which case it will never have risen
            # to get around this, specify that we're only looking
            # at cases where enable started low in first cycle
            with m.If(hist.valueAt(tb.enable, 0) == 0):
                m.d.comb += Assert(hist.pastRose(tb.enable, 1))
                
                @Verification.depthProbe
                def dp3():
                    m.d.comb += Cover(hist.rose(tb.outflag))
                    
        
        with m.If((hist.valueAt(tb.enable, 0) == 0) 
                    & hist.roseWithin(tb.outflag, 10)):
            
            m.d.comb += Assert(hist.roseWithin(tb.enable, 11))
            
            @Verification.depthProbe
            def dpB():
                m.d.comb += Cover(hist.pastRose(tb.enable, 5))
            
            
        with m.If(hist.roseOnCycle(tb.outflag, 5)):
            m.d.comb += Assert(hist.roseOnCycle(tb.enable, 4))
            
        # if you fell, you can't have risen
        with m.If(hist.fell(tb.enable)):
            m.d.comb += Assert(~(hist.rose(tb.enable)))
            
            # implies a sequence ....-_
            #                         ^
            #                         now low
            m.d.comb += Assert(hist.past(tb.enable) & ~tb.enable)
            
            @Verification.depthProbe
            def dp4():
                m.d.comb += Cover(~(hist.rose(tb.enable)))
                
                
        # if we start time with this sequence
        with m.If(hist.followsSequence(tb.enable, [0,0])):
            with m.If((hist.cycle == 2) & tb.enable): # only look at immediately subequent tick
                m.d.comb += Assert(hist.rose(tb.enable))
                @Verification.depthProbe
                def dp5():
                    m.d.comb += Cover(hist.rose(tb.enable))
            
        # if at any point past was a 0 followed by 1
        with m.If(hist.pastSequenceWas(tb.enable, [0,1])):
            m.d.comb += Assert(hist.pastRose(tb.enable))
            @Verification.depthProbe
            def dp6():
                m.d.comb += Cover(hist.pastRose(tb.enable))
            
        
        with m.If( 
                (hist.valueAt(tb.enable, 0) == 1)
                &
                (hist.cycle == 1)
                &
                ~tb.enable):
            # if we started cycle 0 high
            # we're now low, on cycle 1
            # we fell.
            
            m.d.comb += Assert(hist.fell(tb.enable))
            
            @Verification.depthProbe
            def dp7():
                m.d.comb += Cover(hist.fell(tb.enable))
        
        # if at any point past was high but we are now low,
        # we fell
        with m.If(hist.past(tb.enable) & ~tb.enable):
            m.d.comb += Assert(hist.fell(tb.enable))
            @Verification.depthProbe
            def dp8():
                m.d.comb += Cover(hist.fell(tb.enable))
        
        # if we start time with this sequence
        with m.If(hist.followsSequence(tb.enable, [1,0])):
            with m.If(hist.cycle == 2): # only look at immediately subequent tick
                m.d.comb += Assert(hist.pastFell(tb.enable))
                @Verification.depthProbe
                def dp9():
                    m.d.comb += Cover(hist.pastFell(tb.enable))
                    
        if includeCovers:
            m.d.comb += Cover(hist.roseWithin(tb.enable, 10) & hist.fellOnCycle(tb.outflag, 7))
            
    
    @Verification.coverAndVerify(m, dut, group="risefall")
    def riseAndFallWideSignal(m:Module, tb:TestBenchTest, includeCovers:bool=False):
        
        # if you rose, you can't have fallen
        with m.If(hist.rose(tb.output)):
            m.d.comb += Assert(~(hist.fell(tb.output)))
            
            # this implies a sequence 0, non-0
            # using boolean logic with signals and values is tricky, instead
            # use the clear pastFalse/pastTrue/valueFalse/valueTrue or the
            # Verification class helpers isTruewhich does appropriate casting/manips
            m.d.comb += Assert( hist.pastFalse(tb.output) & Verification.valueTrue(tb.output))
            
            @Verification.depthProbe
            def dp1():
                m.d.comb += Cover(~(hist.fell(tb.output)))
                
        
        # the reverse must also be true... if two steps ago was 0, and one 
        # ago went to some non-zero, we rose
        with m.If(hist.pastFalse(tb.output) & Verification.valueTrue(tb.output)):
            m.d.comb += Assert(hist.rose(tb.output))
            
            @Verification.depthProbe
            def dp2():
                m.d.comb += Cover(hist.rose(tb.output))
        
        # if you fell, you can't have risen
        with m.If(hist.fell(tb.output)):
            m.d.comb += Assert(~(hist.rose(tb.output)))
            
            # this implies a sequence non-0, 0
            # using boolean logic with signals and values is tricky, instead
            # use the clear pastFalse/pastTrue which does appropriate casting/manips
            m.d.comb += Assert( hist.pastTrue(tb.output) & hist.valueFalse(tb.output))
            
            @Verification.depthProbe
            def dp3():
                m.d.comb += Cover(~(hist.rose(tb.output)))
        
        
        # the reverse must also be true... if one step ago was high, and now low, we fell
        with m.If(hist.pastTrue(tb.output) & Verification.valueFalse(tb.output)):
            m.d.comb += Assert(hist.fell(tb.output))
            
        
        # the reverse must also be true... if two steps ago was high, and one ago was low, we fell
        with m.If(hist.pastTrue(tb.output, 2) & hist.pastFalse(tb.output)):
            m.d.comb += Assert(hist.pastFell(tb.output))
            
            @Verification.depthProbe
            def dp4():
                m.d.comb += Cover(hist.pastFell(tb.output))
            
            
        # if at any point past was a 0 followed by some non-zero value
        with m.If(
                hist.pastFalse(tb.output)
                &
                hist.valueTrue(tb.output)
            ):
            m.d.comb += Assert(hist.rose(tb.output))
            @Verification.depthProbe
            def dp5():
                m.d.comb += Cover(hist.rose(tb.output))
                
                
                
        # if at any point past was a 0 followed by some non-zero value
        with m.If(hist.pastSequenceWas(tb.output, [0,MaxVal - 3])):
            m.d.comb += Assert(hist.pastRose(tb.output))
            @Verification.depthProbe
            def dp6():
                m.d.comb += Cover(hist.pastRose(tb.output))
                
        
                
        
        with m.If(hist.followsSequence(tb.output, [0,7])):
            with m.If(hist.cycle == 2): # only look at immediately subequent tick
                m.d.comb += Assert(hist.pastRose(tb.output))
                @Verification.depthProbe
                def dp7():
                    m.d.comb += Cover(hist.pastRose(tb.output))
                    
                    
        with m.If( (hist.valueAt(tb.output, 0) == 0)
                   &
                   (hist.valueAt(tb.output, 1) == 7)
                   ):
            with m.If(hist.cycle == 1):
                m.d.comb += Assert(hist.rose(tb.output))
            with m.Elif(hist.cycle == 2):
                m.d.comb += Assert(hist.pastRose(tb.output, 1))
            with m.Elif(hist.cycle == 3):
                m.d.comb += Assert(hist.pastRose(tb.output, 2))
                @Verification.depthProbe
                def dp8():
                    m.d.comb += Cover(hist.pastRose(tb.output, 2))
                            
            
                    
                    
                    
    @Verification.coverAndVerify(m, dut, group="sequence")
    def sequences(m:Module, tb:TestBenchTest, includeCovers:bool=False):
        
        # past is working as we expect.
        # here, output is set by input, one cycle later
        with m.If(hist.past(tb.output) == 22):
            m.d.comb += Assert(hist.past(tb.invalue, 2) == 22)
            @Verification.depthProbe
            def dp1():
                m.d.comb += Cover(hist.past(tb.invalue, 2) == 22)
        
        with m.If(hist.pastWasConstant(tb.invalue, value=8, numCycles=10)):
            for i in range(10):
                m.d.comb += Assert(hist.past(tb.invalue, i+1) == 8)
                
            @Verification.depthProbe
            def dp2():
                m.d.comb += Cover(hist.past(tb.invalue, 2) == 8)
                
        with m.If(hist.pastSequenceWas(tb.output, [1,2,3,4,5])):
            m.d.comb += [
                
                    Assert(hist.past(tb.output, 1) == 5),
                    Assert(hist.past(tb.output, 2) == 4),
                    Assert(hist.past(tb.output, 3) == 3),
                    Assert(hist.past(tb.output, 4) == 2),
                    Assert(hist.past(tb.output, 5) == 1),
                    
                    # and one step behind the output is the 
                    # input that caused it
                    Assert(hist.past(tb.invalue, 1+1) == 5),
                    Assert(hist.past(tb.invalue, 2+1) == 4),
                    Assert(hist.past(tb.invalue, 3+1) == 3),
                    Assert(hist.past(tb.invalue, 4+1) == 2),
                    Assert(hist.past(tb.invalue, 5+1) == 1)
                
                ]
            @Verification.depthProbe
            def dp3():
                m.d.comb += Cover(tb.output == 0xA)
                
        with m.If(hist.followsSequence(tb.invalue, values=[1,2,3,4,5], startCycle=0)):
            with m.If(hist.cycle == 6):
                m.d.comb += [
                    
                        Assert(hist.past(tb.output, 1) == 5),
                        Assert(hist.past(tb.output, 2) == 4),
                        Assert(hist.past(tb.output, 3) == 3),
                        Assert(hist.past(tb.output, 4) == 2),
                        Assert(hist.past(tb.output, 5) == 1)
                    
                    ]
                
                @Verification.depthProbe
                def dp4():
                    m.d.comb += Cover(tb.invalue == 2)
            
            # further down in time, that history is still present,
            # just 5 ticks further down the line now
            with m.If(hist.cycle == 11):
                m.d.comb += [
                    
                        Assert(hist.past(tb.output, 1+5) == 5),
                        Assert(hist.past(tb.output, 2+5) == 4),
                        Assert(hist.past(tb.output, 3+5) == 3),
                        Assert(hist.past(tb.output, 4+5) == 2),
                        Assert(hist.past(tb.output, 5+5) == 1)
                    
                    ]
                
                @Verification.depthProbe
                def dp5():
                    m.d.comb += Cover(tb.invalue == 2)
                
                
        with m.If(hist.pastWasConstant(tb.output, value=7, numCycles=10)):
            for i in range(10):
                m.d.comb += Assert(hist.past(tb.output, i+1) == 7)
            @Verification.depthProbe
            def dp6():
                m.d.comb += Cover(tb.output == 7)
        
        with m.If(hist.isConstant(tb.output, value=8, startCycle=5, numCycles=10)):
            
            with m.If(hist.cycle == 30):
                for i in range(10):
                    m.d.comb += Assert(hist.past(tb.output, 15+i+1) == 8)
                    
                @Verification.depthProbe
                def dp7():
                    m.d.comb += Cover(hist.past(tb.output, 17) == 8)
                
        if includeCovers:
            m.d.comb += Cover(hist.pastSequenceWas(tb.output, [6,7,8,9,10]) & (hist.cycle > 20))
    
    main(m, ports=dut.ports())



