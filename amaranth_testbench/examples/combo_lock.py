
from amaranth import Signal, Elaboratable, Module
from amaranth.build import Platform

KEY1 = 0x42
KEY2 = 0x69 
class ComboLock(Elaboratable):
    '''
        A simple combo lock that will open when it receives 
            KEY1 (0x42)
        followed immediately by
            KEY2 (0x69)
        on input.
        
        It stays open forever after.
    '''
    
    def __init__(self):
    
        # synch num stages param, for embedded edge detector
        self.input = Signal(8)
        self.opened = Signal()
    
    def elaborate(self, platform:Platform):
        m = Module()
        
        first_num_ok = Signal()
        
        with m.If(~self.opened):
            # not open yet
            with m.If(first_num_ok):
                with m.If(self.input == KEY2):
                    m.d.sync += self.opened.eq(1)
                with m.Elif(self.input != KEY1):
                    m.d.sync += first_num_ok.eq(0)
            with m.Else():
                # haven't got first good value yet.
                with m.If(self.input == KEY1):
                    m.d.sync += first_num_ok.eq(1)
                    
        return m

    def ports(self):
        return [self.input, self.opened]
    


if __name__ == "__main__":
    # allow us to run this directly
    from amaranth.cli import main
    
    m = Module() # top level
    m.submodules.combolock = dev = ComboLock()
    main(m, ports=dev.ports())



